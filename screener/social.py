# social.py
# Social Media Post Generator — Phase 3 Module 5
# Generates ready-to-post content for X and LinkedIn
# Triggered by: weekly performance, new positions, milestones
# All posts require manual review before publishing

import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from positions import POSITIONS, CASH, LAST_UPDATED
from universe import UNIVERSE


# --- X Post Templates (280 char limit) ---

def generate_weekly_performance_post(portfolio_value, cost_basis, 
                                      top_performer, top_pct):
    """
    Generate weekly portfolio performance X post.
    """
    total_return = ((portfolio_value - cost_basis) / cost_basis) * 100
    direction    = "+" if total_return >= 0 else ""
    
    context = " (broad market selloff — thesis intact)" if total_return < 0 else ""
    
    post = (
        f"🛡️ Second Layer Capital — Weekly Update\n\n"
        f"Portfolio: {direction}{total_return:.1f}% since inception{context}\n"
        f"Top performer: ${top_performer} (+{top_pct:.1f}%)\n\n"
        f"9 positions. 4 domains. Picks-and-shovels defense thesis.\n\n"
        f"#SecondLayerCapital #DefenseTech #Hypersonics"
    )
        
    return _trim_to_limit(post, 280)


def generate_new_position_post(ticker, company, rationale, amount):
    """
    Generate new position announcement X post.
    """
    post = (
        f"🛡️ Second Layer Capital — New Position\n\n"
        f"Added ${ticker} ({company})\n"
        f"${amount:.0f} initial position\n\n"
        f"{rationale}\n\n"
        f"#SecondLayerCapital #DefenseTech"
    )
    
    return _trim_to_limit(post, 280)


def generate_milestone_post(milestone, detail):
    """
    Generate portfolio milestone X post.
    """
    post = (
        f"🛡️ Second Layer Capital\n\n"
        f"Milestone: {milestone}\n\n"
        f"{detail}\n\n"
        f"Picks-and-shovels play on next-gen defense. "
        f"Built by a 21-year Army vet.\n\n"
        f"#SecondLayerCapital #DefenseTech"
    )
    
    return _trim_to_limit(post, 280)


def generate_thesis_validation_post(ticker, event, impact):
    """
    Generate thesis validation X post — when a holding 
    validates the investment thesis.
    """
    post = (
        f"🛡️ Second Layer Capital — Thesis Validated\n\n"
        f"${ticker}: {event}\n\n"
        f"{impact}\n\n"
        f"This is why we own the supply chain, not the primes.\n\n"
        f"#SecondLayerCapital #DefenseTech #PicksAndShovels"
    )
    
    return _trim_to_limit(post, 280)


# --- LinkedIn Post Templates (longer form) ---

def generate_linkedin_weekly(portfolio_value, cost_basis,
                              posture, top_holdings):
    """
    Generate weekly LinkedIn update — more detailed than X.
    """
    total_return = ((portfolio_value - cost_basis) / cost_basis) * 100
    direction    = "+" if total_return >= 0 else ""
    today        = date.today().strftime("%B %d, %Y")

    post = f"""🛡️ Second Layer Capital — Weekly Portfolio Update
{today}

Portfolio performance since inception: {direction}{total_return:.1f}%{"  (broad market selloff — thesis intact)" if total_return < 0 else ""}
Universe posture: {posture}
Active positions: {len(POSITIONS)}

The thesis remains intact. We own the picks-and-shovels layer of next-generation defense technology — the specialized suppliers, component manufacturers, and software platforms that prime contractors depend on to build hypersonic weapons, autonomous systems, and directed energy platforms.

Current holdings span four technology domains:
- AI & Autonomy: PLTR, AVAV, KTOS
- Hypersonic, Space & Propulsion: KRMN, HWM, ATI
- IoMT & Digital Battlefield: AXON, TDY, HEI, LOAR, CW
- Industrial Supply Chain: MTRN

The system is rules-based, thesis-driven, and fully documented. Every decision has a rationale. Every signal has a source.

Built by a 21-year U.S. Army veteran. Powered by a systematic screener.

#SecondLayerCapital #DefenseTech #Hypersonics #PicksAndShovels #SystematicInvesting"""

    return post


def generate_linkedin_new_position(ticker, company, sector,
                                    rationale, thesis_score):
    """
    Generate LinkedIn new position announcement.
    """
    today = date.today().strftime("%B %d, %Y")

    post = f"""🛡️ Second Layer Capital — New Position Added
{today}

Added ${ticker} — {company}
Sector: {sector}
Thesis Score: {thesis_score}/100

{rationale}

This addition strengthens our exposure to the picks-and-shovels layer of next-generation defense. Not the primes. The supply chain beneath them.

Full thesis and universe documentation available on GitHub.

#SecondLayerCapital #DefenseTech #PicksAndShovels"""

    return post


# --- Utilities ---

def _trim_to_limit(text, limit):
    """Trim post to character limit with ellipsis if needed."""
    if len(text) <= limit:
        return text
    return text[:limit-3] + "..."


def display_post(platform, post_type, content):
    """Display a formatted post for review."""
    print(f"\n{'='*60}")
    print(f"PLATFORM: {platform}")
    print(f"TYPE: {post_type}")
    print(f"LENGTH: {len(content)} chars")
    print(f"{'='*60}")
    print(content)
    print(f"{'='*60}")
    print("⚠️  REVIEW BEFORE POSTING — copy and post manually")


def run_social(post_type="weekly", **kwargs):
    """
    Generate social media posts.
    
    Args:
        post_type: weekly, new_position, milestone, thesis_validation
        **kwargs : parameters for the specific post type
    """
    today = date.today().strftime("%B %d, %Y")
    print(f"Second Layer Capital — Social Media Generator")
    print(f"Date: {today}")
    print(f"Type: {post_type}")

    if post_type == "weekly":
        portfolio_value = kwargs.get("portfolio_value", 0)
        cost_basis      = kwargs.get("cost_basis", 0)
        posture         = kwargs.get("posture", "MIXED")
        top_performer   = kwargs.get("top_performer", "")
        top_pct         = kwargs.get("top_pct", 0)

        x_post = generate_weekly_performance_post(
            portfolio_value, cost_basis, top_performer, top_pct)
        li_post = generate_linkedin_weekly(
            portfolio_value, cost_basis, posture, [])

        display_post("X (Twitter)", "Weekly Performance", x_post)
        display_post("LinkedIn", "Weekly Update", li_post)

    elif post_type == "new_position":
        ticker      = kwargs.get("ticker", "")
        company     = kwargs.get("company", "")
        sector      = kwargs.get("sector", "")
        rationale   = kwargs.get("rationale", "")
        amount      = kwargs.get("amount", 0)
        thesis_score = kwargs.get("thesis_score", 0)

        x_post = generate_new_position_post(
            ticker, company, rationale, amount)
        li_post = generate_linkedin_new_position(
            ticker, company, sector, rationale, thesis_score)

        display_post("X (Twitter)", "New Position", x_post)
        display_post("LinkedIn", "New Position", li_post)

    elif post_type == "milestone":
        milestone = kwargs.get("milestone", "")
        detail    = kwargs.get("detail", "")

        x_post = generate_milestone_post(milestone, detail)
        display_post("X (Twitter)", "Milestone", x_post)

    elif post_type == "thesis_validation":
        ticker = kwargs.get("ticker", "")
        event  = kwargs.get("event", "")
        impact = kwargs.get("impact", "")

        x_post = generate_thesis_validation_post(ticker, event, impact)
        display_post("X (Twitter)", "Thesis Validation", x_post)


if __name__ == "__main__":
    # Demo — weekly post
    run_social(
        post_type       = "weekly",
        portfolio_value = 704.00,
        cost_basis      = 750.00,
        posture         = "MIXED",
        top_performer   = "MTRN",
        top_pct         = 5.2,
    )
