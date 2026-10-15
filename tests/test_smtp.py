"""Unit tests for SMTP Sender and Dry-Run Outbox."""

import tempfile
from pathlib import Path
from agent.tools.smtp_tool import SMTPSenderTool
from agent.models import EmailDraft, ToneType


def test_smtp_dry_run_generates_eml():
    with tempfile.TemporaryDirectory() as tmpdir:
        outbox = Path(tmpdir)
        sender = SMTPSenderTool(dry_run=True, outbox_dir=outbox)

        draft = EmailDraft(
            recipient_name="Dr. Kunal Meher",
            recipient_email="kunal.meher@atlasuniversity.edu.in",
            subject="Experiment 9 Submission",
            body="Here is my assignment submission.",
            tone=ToneType.PROFESSIONAL,
        )

        res = sender.run(draft=draft)
        assert res["success"] is True
        assert res["is_dry_run"] is True

        # Check outbox file exists
        eml_files = list(outbox.glob("*.eml"))
        assert len(eml_files) == 1
        content = eml_files[0].read_text(encoding="utf-8")
        assert "kunal.meher@atlasuniversity.edu.in" in content
        assert "Experiment 9 Submission" in content
