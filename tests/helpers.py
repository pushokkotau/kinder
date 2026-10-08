from app.tinder.models import Recommendation, TinderUser


def recommendation(
    user_id: str,
    photos: list[dict],
    s_number: int = 1,
) -> Recommendation:
    user = TinderUser(
        id=user_id,
        name=user_id,
        photos=photos,
        raw={"_id": user_id},
    )
    return Recommendation(
        user=user,
        s_number=s_number,
        raw={},
    )
