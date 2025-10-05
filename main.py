import requests
import json
from typing import Dict
from dataclasses import dataclass
import streamlit as st
import pandas as pd

@dataclass
class TeamScore:
    team_id: int
    team_name: str
    total_pts: float
    player_count: int
    players: list

def get_team_preview(team_id: int, bearer_token: str) -> Dict:
    """
    Fetch team preview data from the API with Bearer token authentication
    """
    url = f"https://fantaking-api.dunkest.com/api/v1/fantasy-teams/{team_id}/preview"

    headers = {
        'Authorization': f'Bearer {bearer_token}',
        'Content-Type': 'application/json'
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching data for team {team_id}: {e}")
        if hasattr(e.response, 'text'):
            st.error(f"Response: {e.response.text}")
        return None

def calculate_player_points(player: Dict) -> float:
    """
    Calculate points for a player, applying captain multiplier and bench penalty if applicable
    """
    base_pts = player.get('pts', 0)
    is_captain = player.get('is_captain', False)
    captain_multiplier = player.get('captain_multiplier', 1)
    court_position = player.get('court_position', 0)

    # Apply captain multiplier
    if is_captain:
        final_pts = base_pts * captain_multiplier
    else:
        final_pts = base_pts

    # Apply bench penalty (divide by 2) (coach court_position is 11)
    if court_position in [7,8,9,10]:
        final_pts = final_pts / 2

    return final_pts

def calculate_team_points(team_id: int, team_name: str, bearer_token: str) -> TeamScore:
    """
    Calculate total points for a team
    """
    data = get_team_preview(team_id, bearer_token)

    if not data or 'data' not in data or 'players' not in data['data']:
        return TeamScore(team_id=team_id, team_name=team_name, total_pts=0, player_count=0, players=[])

    players = data['data']['players']

    # Calculate total points with captain multiplier and bench penalty
    total_pts = sum(calculate_player_points(player) for player in players)

    return TeamScore(
        team_id=team_id,
        team_name=team_name,
        total_pts=total_pts,
        player_count=len(players),
        players=players
    )

def rank_teams(teams: Dict[str, int], bearer_token: str) -> list[TeamScore]:
    """
    Process all teams and rank them by total points
    """
    team_scores = []

    progress_bar = st.progress(0)
    status_text = st.empty()

    for idx, (team_name, team_id) in enumerate(teams.items()):
        status_text.text(f"Processing team: {team_name} (ID: {team_id})...")
        team_score = calculate_team_points(team_id, team_name, bearer_token)
        team_scores.append(team_score)
        progress_bar.progress((idx + 1) / len(teams))

    status_text.text("Processing complete!")

    # Sort by total_pts in descending order
    team_scores.sort(key=lambda x: x.total_pts, reverse=True)

    return team_scores

def main():
    st.set_page_config(page_title="Fantasy Team Rankings", page_icon="🏀", layout="wide")

    st.title("🏀 Fantasy Team Rankings")
    st.markdown("---")

    # Sidebar for configuration
    with st.sidebar:
        st.header("Configuration")

        # Bearer token input
        bearer_token = st.text_input(
            "Bearer Token",
            type="password",
            help="Enter your API bearer token"
        )

        st.markdown("---")
        st.markdown("### Teams")
        st.info("Teams are configured in the script")

        st.markdown("---")
        st.markdown("### Rules")
        st.info("⭐ Captain points are multiplied by the captain multiplier")
        st.info("🪑 Bench players' points are divided by 2")

    # Dictionary of teams: {team_name: team_id}
    teams = {
        "Memos": 1608378,
        "Karpetis": 1751027,
        "Thanasis": 1751028,
        "Thomas": 1751031,
        "Mitsos": 1751024,
        "TP": 1896177
    }

    if not bearer_token:
        st.warning("⚠️ Please enter your Bearer token in the sidebar to continue")
        return

    if st.button("🔄 Fetch Rankings", type="primary"):
        with st.spinner("Fetching team data..."):
            # Rank teams
            team_scores = rank_teams(teams, bearer_token)

            # Create DataFrame for rankings
            rankings_data = []
            for rank, ts in enumerate(team_scores, 1):
                rankings_data.append({
                    'Rank': rank,
                    'Team Name': ts.team_name,
                    'Team ID': ts.team_id,
                    'Total Points': ts.total_pts,
                    'Players': ts.player_count
                })

            df = pd.DataFrame(rankings_data)

            # Display rankings
            st.markdown("## 🏆 Team Rankings")

            st.dataframe(df, use_container_width=True, hide_index=True)

            # Display metrics for top 3
            st.markdown("## 🥇 Top 3 Teams")
            cols = st.columns(3)

            for idx, ts in enumerate(team_scores[:3]):
                with cols[idx]:
                    medal = ["🥇", "🥈", "🥉"][idx]
                    st.metric(
                        label=f"{medal} {ts.team_name}",
                        value=f"{ts.total_pts:.1f} pts",
                        delta=f"{ts.player_count} players"
                    )

            # Expandable sections for each team's players
            st.markdown("---")
            st.markdown("## 👥 Team Details")

            for rank, ts in enumerate(team_scores, 1):
                with st.expander(f"#{rank} - {ts.team_name} ({ts.total_pts:.1f} pts)"):
                    if ts.players:
                        players_data = []
                        for p in ts.players:
                            base_pts = p.get('pts', 0)
                            is_captain = p.get('is_captain', False)
                            captain_multiplier = p.get('captain_multiplier', 1)
                            court_position = p.get('court_position', 0)

                            was_on_bench = court_position in [7,8,9,10]
                            final_pts = calculate_player_points(p)

                            # Build modifier string
                            modifiers = []
                            if is_captain:
                                modifiers.append(f"x{captain_multiplier}")
                            if was_on_bench:
                                modifiers.append("÷2")
                            modifier_str = " ".join(modifiers) if modifiers else "-"

                            players_data.append({
                                'Name': f"{p.get('first_name', '')} {p.get('last_name', '')}",
                                'Position': p.get('position', {}).get('name', 'Unknown'),
                                'Team': p.get('team', {}).get('abbreviation', 'N/A'),
                                'Base Points': base_pts,
                                'Modifiers': modifier_str,
                                'Final Points': final_pts,
                                'Quotation': p.get('quotation', 0),
                                'Captain': '⭐' if is_captain else '',
                                'Bench': '🪑' if was_on_bench else ''
                            })

                        players_df = pd.DataFrame(players_data)
                        st.dataframe(players_df, use_container_width=True, hide_index=True)
                    else:
                        st.info("No player data available")


if __name__ == "__main__":
    main()
