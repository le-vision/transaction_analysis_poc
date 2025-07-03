# Bank Transaction Analysis Tool

This tool analyzes your bank transaction data, providing insights through visualizations and LLM-powered commentary.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Install Ollama locally:
```bash
brew install ollama
ollama run llama2
```

## Usage

Run the analysis script:
```bash
python transaction_analyzer.py
```

The script will:
1. Load and analyze your CSV data
2. Generate visualizations in the `plots` directory
3. Provide LLM-generated insights about your spending patterns

## Features

- Data structure analysis
- Transaction volume visualization
- Transaction type distribution
- Category analysis (if available)
- LLM-powered insights generation

## Note

Ensure your CSV file is properly formatted with at least these columns:
- Date
- Amount
- Type (optional)
- Category (optional)

The script will adapt to your CSV's specific structure.
