# server.py
from fastmcp import FastMCP

mcp = FastMCP("Demo for AI Summer Days MCP workshop")

@mcp.tool
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return int(a) + int(b)

@mcp.tool
def compound_interest(principal: float, annual_rate: float, compounds_per_year: int, years: float) -> dict:
    """
    Calculate compound interest investment returns.
    
    Formula: A = P(1 + r/n)^(nt)
    
    Args:
        principal: Initial investment amount (P)
        annual_rate: Annual interest rate as decimal (r) - e.g., 0.06 for 6%
        compounds_per_year: Number of times interest compounds per year (n) - e.g., 12 for monthly
        years: Time period in years (t)
    
    Returns:
        Dictionary with final amount, interest earned, and calculation details
    
    Example:
        compound_interest(5000, 0.06, 12, 13) calculates $5,000 at 6% compounded monthly for 13 years
    """
    # A = P(1 + r/n)^(nt)
    final_amount = principal * (1 + annual_rate / compounds_per_year) ** (compounds_per_year * years)
    interest_earned = final_amount - principal
    
    return {
        "principal": principal,
        "annual_rate_percent": annual_rate * 100,
        "compounds_per_year": compounds_per_year,
        "years": years,
        "final_amount": round(final_amount, 2),
        "interest_earned": round(interest_earned, 2),
        "total_return_percent": round((interest_earned / principal) * 100, 2)
    }

if __name__ == "__main__":
    mcp.run()
