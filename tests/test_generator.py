import pytest
from unittest.mock import patch, MagicMock
from generator.minutes import MinutesGenerator


@pytest.fixture
def mock_client():
    with patch("generator.minutes.genai") as mock_genai:
        mock_c = MagicMock()
        mock_genai.Client.return_value = mock_c
        yield mock_c


@pytest.fixture
def gen(mock_client):
    return MinutesGenerator(api_key="test-key")


def test_generate_returns_markdown(gen):
    gen._client.models.generate_content.return_value = MagicMock(
        text="# 定例会議 2026-04-26\n\n## 参加者\n山本、田中",
        candidates=[MagicMock()],
    )

    transcript = "[00:00] Speaker1: テスト\n[00:05] Speaker2: テスト2"
    result = gen.generate(transcript)
    assert "# " in result
    assert isinstance(result, str)


def test_build_prompt_includes_format(gen):
    prompt = gen._build_generation_prompt("test transcript")
    assert "アクションアイテム" in prompt
    assert "タイムスタンプ" in prompt


def test_generate_sends_transcript(gen):
    gen._client.models.generate_content.return_value = MagicMock(
        text="# Minutes", candidates=[MagicMock()]
    )

    gen.generate("test transcript")
    call_kwargs = gen._client.models.generate_content.call_args
    assert "test transcript" in str(call_kwargs)


def test_generate_empty_transcript(mock_client):
    g = MinutesGenerator(api_key="test")

    with pytest.raises(ValueError, match="空です"):
        g.generate("")

    with pytest.raises(ValueError, match="空です"):
        g.generate("   ")
