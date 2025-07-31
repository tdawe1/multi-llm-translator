import pytest
from app import parse_languages, get_job_id_from_link

# --- Tests for parse_languages ---

def test_parse_languages_standard():
    """Tests a standard, well-formatted title."""
    title = "Some Job Title | Japanese/English"
    assert parse_languages(title) == ("Japanese", "English")

def test_parse_languages_with_extra_whitespace():
    """Tests that whitespace around the languages is correctly stripped."""
    title = "Another Job |  Spanish /  French  "
    assert parse_languages(title) == ("Spanish", "French")

def test_parse_languages_no_match():
    """Tests a title with no language pair, which should fail gracefully."""
    title = "A job with no language information"
    assert parse_languages(title) == (None, None)

# --- Tests for get_job_id_from_link ---

def test_get_job_id_from_link_standard():
    """Tests a standard job URL with a referral."""
    link = "https://gengo.com/t/jobs/details/33808373?referral=rss"
    assert get_job_id_from_link(link) == "33808373"

def test_get_job_id_from_link_no_referral():
    """Tests a job URL without any query parameters."""
    link = "https://gengo.com/t/jobs/details/12345678"
    assert get_job_id_from_link(link) == "12345678"

def test_get_job_id_from_link_no_match():
    """Tests a URL that doesn't contain a job ID."""
    link = "https://gengo.com/t/jobs/"
    assert get_job_id_from_link(link) is None
