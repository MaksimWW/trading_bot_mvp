
# Deployment Guide

## Prerequisites
- Python 3.8+
- Tinkoff Invest API token
- Telegram Bot token

## Environment Setup

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Configure environment variables in `.env`
4. Run database setup
5. Start the application: `python src/main.py`

## Production Deployment

### On Replit
1. Import project to Replit
2. Set environment variables in Secrets
3. Configure the Run button
4. Deploy using Replit's deployment features

## Configuration
- Set API tokens in environment variables
- Configure risk parameters
- Set up logging levels

## Monitoring
- Check logs in `logs/` directory
- Monitor Telegram bot status
- Track trading performance
