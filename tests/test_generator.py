import pytest
from unittest.mock import patch, MagicMock
from generator.minutes import MinutesGenerator

@pytest.fixture
def gen():
    return MinutesGenerator(api_key="test-key")

@patch("generator.minutes.genai")
def test_generate_returns_markdown(mock_genai, gen):
    mock_model = MagicMock()
    mock_model.generate_content.return_value = MagicMock(
        text="# 定例会議 2026-04-26\n\n## 参加者\n山本、田中"
    )
    mock_genai.GenerativeModel.return_value = mock_model

    transcript = "[00:00] Speaker1: テスト\n[00:05] Speaker2: テスト2"
    result = gen.generate(transcript)
    assert "# " in result
    assert isinstance(result, str)

def test_build_prompt_includes_format(gen):
    prompt = gen._build_generation_prompt("test transcript")
    assert "アクションアイテム" in prompt
    assert "タイムスタンプ" in prompt

@patch("generator.minutes.genai")
def test_generate_sends_transcript(mock_genai, gen):
    mock_model = MagicMock()
    mock_model.generate_content.return_value = MagicMock(text="# Minutes")
    mock_genai.GenerativeModel.return_value = mock_model

    gen.generate("test transcript")
    call_args = mock_model.generate_content.call_args[0][0]
    assert "test transcript" in call_args
