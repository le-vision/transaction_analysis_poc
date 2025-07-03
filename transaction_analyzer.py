import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
from datetime import datetime
import ollama
from dotenv import load_dotenv
from typing import Optional, Dict, Any, TextIO

# Load environment variables
load_dotenv()

# Configuration constants
CONFIG = {
    'PLOTS_DIR': os.getenv('PLOTS_DIR', 'plots'),
    'REPORT_DIR': os.getenv('REPORT_DIR', 'report'),
    'LLM_MODEL': os.getenv('LLM_MODEL', 'llama2'),
    'JUDGE_MODEL': os.getenv('JUDGE_MODEL', 'mistral')
}

# Column name mappings and constants
COLUMN_CONFIG = {
    'DATE': 'Transaction Date',
    'DEBIT': 'Debit Amount',
    'CREDIT': 'Credit Amount',
    'TYPE': 'Transaction Type',
    'DESCRIPTION': 'Transaction Description',
    'CATEGORY': 'Category'
}

class TransactionAnalyzer:
    """
    Analyzes bank transaction data and generates comprehensive reports.
    
    Args:
        csv_path (str): Path to the CSV file containing transaction data
        plots_dir (str): Directory to save generated plots
        report_dir (str): Directory to save generated reports
    """
    
    def __init__(self, csv_path: str, plots_dir: Optional[str] = None, report_dir: Optional[str] = None):
        """
        Initialize the TransactionAnalyzer.
        
        Args:
            csv_path (str): Path to the CSV file containing transaction data
            plots_dir (str, optional): Directory to save generated plots
            report_dir (str, optional): Directory to save generated reports
        """
        print("Initializing TransactionAnalyzer...")
        self.csv_path = csv_path
        self.df = None
        self.plots_dir = plots_dir or CONFIG['PLOTS_DIR']
        self.report_dir = report_dir or CONFIG['REPORT_DIR']
        print(f"Using plots directory: {self.plots_dir}")
        print(f"Using report directory: {self.report_dir}")
        print("Calling load_data()...")
        self.load_data()
        
    def load_data(self):
        """
        Load transaction data from CSV file.
        
        Raises:
            FileNotFoundError: If the CSV file is not found
            pd.errors.EmptyDataError: If the CSV file is empty
        """
        try:
            print("Loading data...")
            self.df = pd.read_csv(self.csv_path)
            print("\nData loaded successfully!\n")
            print("First few rows of data:")
            print(self.df.head())
            print("\nData types:")
            print(self.df.dtypes)
            
            # Preprocess the data immediately after loading
            print("Preprocessing data...")
            self._preprocess_data()
            
        except FileNotFoundError as e:
            raise FileNotFoundError(f"Error: CSV file not found at {self.csv_path}") from e
        except pd.errors.EmptyDataError as e:
            raise pd.errors.EmptyDataError(f"Error: CSV file is empty") from e
        except Exception as e:
            raise Exception(f"Error loading data: {e}") from e
    
    def _preprocess_data(self):
        """
        Preprocess the data by:
        1. Converting date columns to datetime
        2. Converting amount columns to numeric
        3. Standardizing column names
        4. Handling missing values
        """
        try:
            # Convert date column to datetime
            if COLUMN_CONFIG['DATE'] in self.df.columns:
                self.df[COLUMN_CONFIG['DATE']] = pd.to_datetime(
                    self.df[COLUMN_CONFIG['DATE']], 
                    format='%d/%m/%Y', 
                    errors='coerce'
                )
                
                # Handle NaT values
                if self.df[COLUMN_CONFIG['DATE']].isna().any():
                    print("Warning: Some dates could not be parsed. These rows will be dropped.")
                    self.df = self.df.dropna(subset=[COLUMN_CONFIG['DATE']])
            
            # Convert amount columns to numeric with improved error handling
            for col in [COLUMN_CONFIG['DEBIT'], COLUMN_CONFIG['CREDIT']]:
                # If column doesn't exist, create it with zeros
                if col not in self.df.columns:
                    print(f"Warning: {col} column not found. Creating new column with zeros.")
                    self.df[col] = pd.Series(0.0, index=self.df.index)
                    continue
                
                # If column exists but is empty, fill with zeros
                if self.df[col].isna().all():
                    print(f"Warning: {col} column is entirely empty. Filling with zeros.")
                    self.df[col] = 0.0
                    continue
                
                # Ensure column is string type before processing
                try:
                    # Convert to string if not already string or numeric
                    if not pd.api.types.is_numeric_dtype(self.df[col]) and not pd.api.types.is_string_dtype(self.df[col]):
                        self.df[col] = self.df[col].astype(str)
                    
                    # Remove any currency symbols and commas
                    self.df[col] = self.df[col].astype(str)  # Ensure string type for replacements
                    self.df[col] = self.df[col].str.replace('£', '', regex=False)
                    self.df[col] = self.df[col].str.replace(',', '', regex=False)
                    self.df[col] = self.df[col].str.replace(' ', '', regex=False)  # Remove spaces
                    
                    # Convert to numeric with error handling
                    self.df[col] = pd.to_numeric(self.df[col], errors='coerce')
                    
                    # Handle NaN values by converting to 0
                    if self.df[col].isna().any():
                        print(f"Warning: Some values in {col} could not be converted to numeric. These will be set to 0.")
                        self.df[col] = self.df[col].fillna(0)
                        
                    # Ensure final type is float
                    self.df[col] = self.df[col].astype(float)
                except Exception as e:
                    print(f"Error processing {col}: {str(e)}")
                    print(f"Setting all values in {col} to 0 as fallback.")
                    self.df[col] = 0.0
            
            # Standardize column names
            self.df.columns = self.df.columns.str.strip()
            
        except KeyError as e:
            raise KeyError(f"Required column not found: {e}")
        except Exception as e:
            raise Exception(f"Error preprocessing data: {e}")
    
    def _create_and_save_plot(self, plot_type: str, data: Any, title: str, filename: str, **kwargs):
        """
        Helper method to create and save plots consistently.
        
        Args:
            plot_type (str): Type of plot (e.g., 'bar', 'pie')
            data (Any): Data to plot
            title (str): Plot title
            filename (str): Output filename
            **kwargs: Additional plotting parameters
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(self.plots_dir, exist_ok=True)
            
            plt.figure(figsize=kwargs.get('figsize', (12, 6)))
            
            # Remove rotation from kwargs if it exists
            rotation = kwargs.pop('rotation', None)
            
            if plot_type == 'bar':
                data.plot(kind='bar', **kwargs)
                if rotation:
                    plt.xticks(rotation=rotation, ha='right')
            elif plot_type == 'pie':
                data.plot(kind='pie', autopct='%1.1f%%', **kwargs)
            elif plot_type == 'line':
                data.plot(kind='line', **kwargs)
            else:
                raise ValueError(f"Unsupported plot type: {plot_type}")
            
            plt.title(title)
            plt.tight_layout()
            
            # Add axis labels if provided
            if 'xlabel' in kwargs:
                plt.xlabel(kwargs['xlabel'])
            if 'ylabel' in kwargs:
                plt.ylabel(kwargs['ylabel'])
            
            # Save and close plot
            filepath = os.path.join(self.plots_dir, filename)
            plt.savefig(filepath)
            plt.close()
            
            return filepath
            
        except Exception as e:
            raise Exception(f"Error creating plot {filename}: {e}")
    
    def _check_ollama_connection(self) -> bool:
        """
        Check if Ollama service is available and accessible.
        
        Returns:
            bool: True if Ollama is available, False otherwise
        
        Logs:
            Any connection errors will be logged internally
        """
        try:
            client = ollama.Client()
            # Try a simple list models call to check connection
            models = client.list()
            return True
        except Exception as e:
            print(f"Warning: Could not connect to Ollama service: {e}")
            return False
    
    def analyze_structure(self) -> Dict[str, Any]:
        """
        Analyze the structure of the transaction data and return analysis results.
        
        Returns:
            dict: Dictionary containing data structure analysis
        """
        if self.df.empty:
            return {
                'basic_info': {
                    'num_transactions': 0,
                    'time_period': {
                        'start': None,
                        'end': None
                    },
                    'amounts': {
                        'total_debit': 0.0,
                        'total_credit': 0.0
                    }
                },
                'missing_values': {},
                'summary_stats': {},
                'warning': 'No data available for analysis'
            }
        
        analysis = {
            'basic_info': {
                'num_transactions': len(self.df),
                'time_period': {
                    'start': self.df[COLUMN_CONFIG['DATE']].min(),
                    'end': self.df[COLUMN_CONFIG['DATE']].max()
                },
                'amounts': {
                    'total_debit': self.df[COLUMN_CONFIG['DEBIT']].sum(),
                    'total_credit': self.df[COLUMN_CONFIG['CREDIT']].sum()
                }
            },
            'missing_values': self.df.isnull().sum().to_dict(),
            'summary_stats': self.df.describe().to_dict()
        }
        
        return analysis
    
    def visualize_transactions(self) -> Dict[str, str]:
        """
        Generate visualizations of transaction data.
        
        Returns:
            dict: Dictionary containing paths to generated plots
        """
        if self.df.empty:
            return {
                'warning': 'No data available for visualization'
            }
        
        plots = {}
        
        try:
            # Monthly transaction volume
            monthly_counts = self.df.groupby(self.df[COLUMN_CONFIG['DATE']].dt.to_period('M')).size()
            plots['monthly_volume'] = self._create_and_save_plot(
                'bar',
                monthly_counts,
                'Monthly Transaction Volume',
                'monthly_volume.png',
                xlabel='Month',
                ylabel='Number of Transactions'
            )
            
            # Transaction type distribution
            if COLUMN_CONFIG['TYPE'] in self.df.columns:
                type_counts = self.df[COLUMN_CONFIG['TYPE']].value_counts()
                plots['type_distribution'] = self._create_and_save_plot(
                    'bar',
                    type_counts,
                    'Transaction Type Distribution',
                    'type_distribution.png',
                    xlabel='Transaction Type',
                    ylabel='Number of Transactions'
                )
            
            # Top categories by amount
            if COLUMN_CONFIG['DESCRIPTION'] in self.df.columns:
                category_amounts = self.df.groupby(COLUMN_CONFIG['DESCRIPTION'])[COLUMN_CONFIG['DEBIT']].sum()
                top_categories = category_amounts.nlargest(10)
                plots['top_categories'] = self._create_and_save_plot(
                    'bar',
                    top_categories,
                    'Top 10 Categories by Amount',
                    'top_categories.png',
                    xlabel='Category',
                    ylabel='Amount',
                    rotation=45
                )
            
            return plots
            
        except Exception as e:
            raise Exception(f"Error generating visualizations: {e}")
    
    def get_llm_insights(self) -> str:
        """
        Generate insights using LLM.
        
        Returns:
            str: LLM-generated insights or fallback message if LLM is unavailable
        """
        if self.df.empty:
            return "No data available for analysis"
        
        try:
            # Check Ollama connection
            if not self._check_ollama_connection():
                return "LLM service is currently unavailable. Please ensure Ollama is running and accessible."
                
            client = ollama.Client()
            
            # Generate insights
            response = client.generate(
                model=CONFIG['LLM_MODEL'],
                prompt=f"""
                Analyze the following transaction data structure and provide insights:
                {self.df.describe().to_string()}
                
                Key observations from the data:
                1. Number of transactions: {len(self.df)}
                2. Time period covered: {self.df[COLUMN_CONFIG['DATE']].min()} to {self.df[COLUMN_CONFIG['DATE']].max()}
                3. Total amount: £{self.df[COLUMN_CONFIG['DEBIT']].sum():,.2f}
                
                Please provide:
                1. 3-5 key insights about spending patterns and financial behavior
                2. Any notable trends in transaction volume
                3. Recommendations for financial optimization
                
                Format your response in markdown format with clear sections.
                """
            )
            
            return response.response
            
        except Exception as e:
            print(f"Warning: Error generating LLM insights: {e}")
            return f"Error generating LLM insights: {str(e)}\nPlease check the Ollama service and try again."
    
    def get_judge_evaluation(self, analysis: dict, insights: str) -> str:
        """
        Get evaluation from a judge LLM model.
        
        Args:
            analysis (dict): Data analysis results
            insights (str): LLM-generated insights
            
        Returns:
            str: Judge's evaluation or fallback message if LLM is unavailable
        """
        max_retries = 3
        retry_delay = 5  # seconds
        
        for attempt in range(max_retries):
            try:
                # Check Ollama connection
                if not self._check_ollama_connection():
                    return "LLM service is currently unavailable. Please ensure Ollama is running and accessible."
                    
                client = ollama.Client()
                
                # Generate evaluation
                response = client.generate(
                    model=CONFIG['JUDGE_MODEL'],
                    prompt=f"""
                    Evaluate the following data analysis and LLM-generated insights:
                    
                    Data Analysis:
                    {analysis}
                    
                    Generated Insights:
                    {insights}
                    
                    Please provide:
                    1. Evaluation of the accuracy and relevance of the insights
                    2. Suggestions for improvement in the analysis
                    3. Overall assessment of the financial recommendations
                    
                    Format your response in markdown format with clear sections.
                    """
                )
                
                return response.response
                
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"Warning: Error generating judge evaluation (attempt {attempt + 1}/{max_retries}): {e}")
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    print(f"Warning: Error generating judge evaluation (attempt {attempt + 1}/{max_retries}): {e}")
                    return f"Error generating judge evaluation: {str(e)}\nPlease check the Ollama service and try again."

    def _write_report_header(self, f: TextIO) -> None:
        """
        Write the report header.
        
        Args:
            f: TextIO: File object to write to
        """
        f.write("# Bank Transaction Analysis Report\n\n")
        f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

    def _write_structure_analysis(self, f: TextIO, analysis: Dict[str, Any]) -> None:
        """
        Write the data structure analysis section.
        
        Args:
            f: TextIO: File object to write to
            analysis: Dict[str, Any]: Analysis results
        """
        f.write("## Data Structure Analysis\n\n")
        
        if 'warning' in analysis:
            f.write(f"**Warning:** {analysis['warning']}\n\n")
            return
            
        f.write(f"Number of transactions: {analysis['basic_info']['num_transactions']}\n\n")
        f.write(f"Time period: {analysis['basic_info']['time_period']['start']} to {analysis['basic_info']['time_period']['end']}\n\n")
        f.write(f"Total amount: £{analysis['basic_info']['amounts']['total_debit']:,.2f}\n\n")
        f.write("### Missing Values\n\n")
        missing_values_df = pd.DataFrame.from_dict(analysis['missing_values'], orient='index')
        f.write(f"{missing_values_df.to_string()}\n\n")
        f.write("### Summary Statistics\n\n")
        summary_stats_df = pd.DataFrame(analysis['summary_stats'])
        f.write(f"{summary_stats_df.to_string()}\n\n")

    def _write_visualizations(self, f: TextIO, plots: Dict[str, str]) -> None:
        """
        Write the visualizations section.
        
        Args:
            f: TextIO: File object to write to
            plots: Dict[str, str]: Dictionary of plot names and paths
        """
        f.write("## Visualizations\n\n")
        
        if 'warning' in plots:
            f.write(f"**Warning:** {plots['warning']}\n\n")
            return
            
        for plot_name, plot_path in plots.items():
            f.write(f"### {plot_name.replace('_', ' ').title()}\n\n")
            f.write(f"![{plot_name}]({plot_path})\n\n")

    def _write_llm_insights(self, f: TextIO, insights: str) -> None:
        """
        Write the LLM insights section.
        
        Args:
            f: TextIO: File object to write to
            insights: str: LLM-generated insights
        """
        f.write("## LLM Insights\n\n")
        f.write(insights + "\n\n")

    def _write_judge_evaluation(self, f: TextIO, evaluation: str) -> None:
        """
        Write the judge evaluation section.
        
        Args:
            f: TextIO: File object to write to
            evaluation: str: Judge's evaluation
        """
        f.write("## Expert Review\n\n")
        f.write(evaluation + "\n\n")

    def generate_report(self) -> str:
        """
        Generate a comprehensive analysis report.
        
        Returns:
            str: Path to the generated report
        """
        try:
            os.makedirs(self.report_dir, exist_ok=True)
            report_path = os.path.join(self.report_dir, 'analysis_report.md')
            
            with open(report_path, 'w') as f:
                self._write_report_header(f)
                
                analysis = self.analyze_structure()
                self._write_structure_analysis(f, analysis)
                
                plots = self.visualize_transactions()
                self._write_visualizations(f, plots)
                
                insights = self.get_llm_insights()
                self._write_llm_insights(f, insights)
                
                evaluation = self.get_judge_evaluation(analysis, insights)
                self._write_judge_evaluation(f, evaluation)
            
            print(f"\nReport generated successfully at: {report_path}")
            return report_path
            
        except Exception as e:
            raise Exception(f"Error generating report: {e}")

def _write_llm_insights(self, f: TextIO, insights: str) -> None:
    """
    Write the LLM insights section.
    
    Args:
        f: TextIO: File object to write to
        insights: str: LLM-generated insights
    """
    f.write("## LLM Insights\n\n")
    f.write(insights + "\n\n")

def _write_judge_evaluation(self, f: TextIO, evaluation: str) -> None:
    """
    Write the judge evaluation section.
    
    Args:
        f: TextIO: File object to write to
        evaluation: str: Judge's evaluation
    """
    f.write("## Expert Review\n\n")
    f.write(evaluation + "\n\n")

def main():
    """
    Main entry point for the transaction analyzer.
    """
    try:
        # Initialize analyzer with CSV path
        analyzer = TransactionAnalyzer(
            "./00472782_20250824_0806.csv",
            plots_dir=os.getenv('PLOTS_DIR'),
            report_dir=os.getenv('REPORT_DIR')
        )
        
        # Generate comprehensive report
        report_path = analyzer.generate_report()
        print(f"\nReport generated at: {report_path}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        print("Full traceback:")
        print(traceback.format_exc())

if __name__ == "__main__":
    main()
