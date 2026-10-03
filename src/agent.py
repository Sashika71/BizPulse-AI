from crewai import Agent, Task, Crew, Process, LLM
from src.config import Config

def create_bizpulse_crew(rates, raw_news):
    # Initialize Gemini LLM securely using Google AI Studio API key
    llm = LLM(
        model=f"gemini/{Config.GEMINI_MODEL}",
        api_key=Config.GEMINI_API_KEY,
    )

    # 1. News Researcher Agent
    news_researcher = Agent(
        role='Senior Business News Researcher',
        goal='Analyze raw news headlines and select the most impactful local and global business updates for executives.',
        backstory='An expert researcher skilled at filtering important economic and corporate news from noise.',
        verbose=True,
        llm=llm,
        allow_delegation=False
    )

    # 2. Financial Analyst Agent
    financial_analyst = Agent(
        role='Market & Rates Analyst',
        goal='Organize and present exact pre-fetched financial numbers cleanly.',
        backstory=(
            'A meticulous financial analyst. '
            'CRITICAL RULE: You must NEVER alter, round off, or invent financial numbers. '
            'You must strictly preserve the exact numbers provided to you.'
        ),
        verbose=True,
        llm=llm,
        allow_delegation=False
    )

    # 3. Executive Writer & Formatter Agent
    email_formatter = Agent(
        role='Executive Newsletter Formatter',
        goal='Compile research and analysis into a crisp, professional daily morning email briefing.',
        backstory='A professional business copywriter who specializes in executive morning briefings.',
        verbose=True,
        llm=llm,
        allow_delegation=False
    )

    # Define Tasks
    task_research = Task(
        description=f"""
        Review the following raw news headlines and select top updates for Sri Lankan and global businessmen, 
        and format them clearly with a 'Why it matters' business impact note for each:
        {raw_news}
        """,
        expected_output="Curated local and global headlines structured with 'Why it matters' notes.",
        agent=news_researcher
    )

    task_analysis = Task(
        description=f"""
        Take these verified financial numbers and structure them into the exact clean market snapshot table format:
        - USD to LKR Rate: {rates['USD_LKR']}
        - Gold Price: {rates['Gold_Price_USD']}
        - CSE Market Index: {rates['CSE_Index']}
        """,
        expected_output="A clean structured market snapshot table.",
        agent=financial_analyst
    )

    task_formatting = Task(
        description="""
        Combine the market snapshot table and the curated headlines into a professional, HTML-ready daily morning briefing.
        Ensure it matches this exact clean aesthetic:
        
        📊 Market Snapshot
        [Table with Indicator | Latest | Change]
        
        🇱🇰 Local Headlines & 🌍 Global Headlines
        (With clear numbering, brief text, and 'Why it matters' business context)
        """,
        expected_output="A professionally formatted HTML daily business briefing email body.",
        agent=email_formatter
    )

    return Crew(
        agents=[news_researcher, financial_analyst, email_formatter],
        tasks=[task_research, task_analysis, task_formatting],
        process=Process.sequential,
        verbose=True
    )