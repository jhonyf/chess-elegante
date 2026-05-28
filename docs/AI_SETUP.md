# AI Commentary Setup

The Chess Analyzer now includes AI-powered move commentary powered by Claude AI, written in the style of Irving Chernev's "Logical Chess: Move by Move."

## Setup Instructions

### 1. Install Dependencies

First, install the required packages:

```bash
pip install -r requirements.txt
```

### 2. Get an Anthropic API Key

1. Visit [https://console.anthropic.com/](https://console.anthropic.com/)
2. Sign up or log in to your account
3. Navigate to API Keys section
4. Create a new API key
5. Copy the key (it will only be shown once!)

### 3. Configure Environment Variables

Add your API key to your `.env` file:

```bash
# Copy the example file if you haven't already
cp .env.example .env

# Edit .env and add your Anthropic API key
ANTHROPIC_API_KEY=your_actual_api_key_here
```

### 4. Start the Application

```bash
python app.py
```

## Features

When you make a move, the AI will provide:

- **Move Analysis**: Educational commentary on why the move is good or bad
- **Strategic Context**: Explanation of the position and what you should be looking for
- **Improvement Suggestions**: If you made a mistake, clear guidance on what you should have done

## Example Commentary

For a good move:
> "This knight development to f3 is excellent. It controls the central squares e5 and d4 while preparing to castle kingside. The knight is well-placed to support your center and creates no weaknesses in your position."

For a mistake:
> "Moving the knight to c4 hangs it to the d5 pawn. While you can recapture with the bishop, you've wasted time and allowed Black to improve their position. The better move was Nb1, retreating to safety while maintaining your defensive setup."

## Cost Considerations

- Each move evaluation calls the Claude API once
- Cost is approximately $0.003 per move (3/10 of a cent)
- A typical 40-move game would cost ~$0.12
- You can disable AI commentary by not setting the `ANTHROPIC_API_KEY` environment variable

## Troubleshooting

If AI commentary is not showing up:

1. Check that your API key is correctly set in `.env`
2. Check the console output for error messages
3. Ensure you have installed the `anthropic` package
4. Verify your API key has sufficient credits at [https://console.anthropic.com/](https://console.anthropic.com/)

The application will continue to work without AI commentary if the API key is not configured - you'll just see the standard move evaluation without the narrative commentary.
