"""Preference-based movie, series, and music recommendation engine using persistent user memory."""

from typing import Any, Dict, List, Optional

from mitchell.core.llm import model_router
from mitchell.memory.self_model import self_model


class MediaRecommender:
    """Generates personalized entertainment suggestions based on user model preferences."""

    def __init__(self) -> None:
        self.self_model = self_model
        self.router = model_router

    async def get_recommendations(
        self,
        media_type: str = "movie",
        mood_or_genre: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Synthesize personalized recommendations considering user taste."""
        user_context = self.self_model.get_user_context_summary()

        prompt = (
            f"Recommend 5 standout {media_type}s for the user.\n"
            f"User Profile & Taste Context:\n{user_context}\n"
            f"Specific Request / Mood / Genre: {mood_or_genre or 'top rated'}\n"
            "Format your response as a numbered list with: Title (Year), Genre, and Why you'll love it."
        )

        res = await self.router.generate(prompt=prompt, purpose="media_recommendation")
        # Structure suggestions
        lines = [l.strip() for l in res.content.splitlines() if l.strip() and (l[0].isdigit() or l.startswith("-"))]
        suggestions = []
        for line in lines:
            suggestions.append({"text": line, "type": media_type})

        return suggestions or [{"text": res.content, "type": media_type}]


media_recommender = MediaRecommender()

__all__ = ["MediaRecommender", "media_recommender"]
