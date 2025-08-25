import json
import logging
from typing import Dict, Optional
import httpx
import jmespath

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

client = httpx.Client(
    headers={
        # this is internal ID of an instagram backend app. It doesn't change often.
        "x-ig-app-id": "936619743392459",
        # use browser-like features
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9,ru;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept": "*/*",
    },
    timeout=10.0,
)


def scrape_user(username: str) -> Dict:
    """Scrape Instagram user's data via the web_profile_info endpoint."""
    result = client.get(
        f"https://i.instagram.com/api/v1/users/web_profile_info/?username={username}",
    )
    result.raise_for_status()
    data = result.json()
    # the structure contains data -> user
    return data["data"]["user"]


def parse_user(data: Dict) -> Dict:
    """Parse instagram user's hidden web dataset for user's data using jmespath."""
    log.debug("parsing user data %s", data.get('username'))
    result = jmespath.search(
        r"""{
        name: full_name,
        username: username,
        id: id,
        category: category_name,
        business_category: business_category_name,
        phone: business_phone_number,
        email: business_email,
        bio: biography,
        bio_links: bio_links[].url,
        homepage: external_url,
        followers: edge_followed_by.count,
        follows: edge_follow.count,
        facebook_id: fbid,
        is_private: is_private,
        is_verified: is_verified,
        profile_image: profile_pic_url_hd,
        video_count: edge_felix_video_timeline.count,
        videos: edge_felix_video_timeline.edges[].node.{
            id: id,
            title: title,
            shortcode: shortcode,
            thumb: display_url,
            url: video_url,
            views: video_view_count,
            tagged: edge_media_to_tagged_user.edges[].node.user.username,
            captions: edge_media_to_caption.edges[].node.text,
            comments_count: edge_media_to_comment.count,
            comments_disabled: comments_disabled,
            taken_at: taken_at_timestamp,
            likes: edge_liked_by.count,
            location: location.name,
            duration: video_duration
        },
        image_count: edge_owner_to_timeline_media.count,
        images: edge_owner_to_timeline_media.edges[].node.{
            id: id,
            title: title,
            shortcode: shortcode,
            src: display_url,
            url: video_url,
            views: video_view_count,
            tagged: edge_media_to_tagged_user.edges[].node.user.username,
            captions: edge_media_to_caption.edges[].node.text,
            comments_count: edge_media_to_comment.count,
            comments_disabled: comments_disabled,
            taken_at: taken_at_timestamp,
            likes: edge_liked_by.count,
            location: location.name,
            accesibility_caption: accessibility_caption,
            duration: video_duration
        },
        saved_count: edge_saved_media.count,
        collections_count: edge_saved_media.count,
        related_profiles: edge_related_profiles.edges[].node.username
    }""",
        data,
    )
    return result


def most_recent_post_url(parsed: Dict) -> Optional[str]:
    """Return the URL of the most recent post (image or video) if available."""
    # prefer images (timeline media), fallback to videos
    media = parsed.get('images') or parsed.get('videos') or []
    if not media:
        return None
    first = media[0]
    shortcode = first.get('shortcode')
    if shortcode:
        return f"https://www.instagram.com/p/{shortcode}/"
    # some nodes may not have shortcode but have id/url
    if first.get('url'):
        return first['url']
    if first.get('src'):
        return first['src']
    return None


def normalize_ts(value) -> Optional[int]:
    """Normalize a timestamp to UNIX seconds (int).

    Accepts int or numeric string. Handles milliseconds by converting to seconds.
    Returns None for invalid input.
    """
    if value is None:
        return None
    try:
        ts = int(value)
    except Exception:
        # sometimes value may be a non-integer string
        try:
            ts = int(float(value))
        except Exception:
            return None
    # if milliseconds (13+ digits) convert to seconds
    if ts > 10**12:
        ts = ts // 1000
    return ts


def ts_to_iso_utc(ts_seconds: int) -> str:
    from datetime import datetime, timezone

    return datetime.fromtimestamp(ts_seconds, tz=timezone.utc).isoformat()


def get_ig_post_img_24h(username):
    try:
        user = scrape_user(username)
    except httpx.HTTPError as e:
        log.error("Failed to fetch user: %s", e)
        raise SystemExit(1)

    parsed = parse_user(user)

    # Filter images taken in the last 24 hours using normalized timestamps
    from datetime import datetime, timezone

    now = int(datetime.now(timezone.utc).timestamp())
    one_day_ago = now - 24 * 60 * 60

    images = parsed.get('images', []) or []
    recent = []
    for img in images:
        taken = img.get('taken_at') or img.get('taken_at_timestamp')
        taken_int = normalize_ts(taken)

        if taken_int is not None and taken_int >= one_day_ago:
            recent.append({
                'shortcode': img.get('shortcode'),
                'src': img.get('src'),
                'taken_at': taken_int,
                'taken_at_iso_utc': ts_to_iso_utc(taken_int),
            })

    if recent:
        return recent
    else:
        return []


if __name__ == "__main__":
    # Hardcode the username here (edit this value directly)
    USERNAME = "launchpadpurdue"
    posts = get_ig_post_img_24h(USERNAME)
    print(json.dumps(posts, indent=2))