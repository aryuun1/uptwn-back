
import re
import uuid
from sqlalchemy.orm import Session
from app.models.title import Title


def generate_slug(text: str) -> str:
    """Convert text to a URL-safe slug: lowercase, hyphens, no special chars."""
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug


def make_unique_slug(db: Session, title_text: str) -> str:
    """Generate a unique slug, appending a short random suffix on collision."""
    base_slug = generate_slug(title_text)
    slug = base_slug
    while db.query(Title.id).filter(Title.slug == slug).first() is not None:
        slug = f"{base_slug}-{uuid.uuid4().hex[:6]}"
    return slug
