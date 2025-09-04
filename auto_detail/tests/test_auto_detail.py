"""Unit tests for auto_detail CLI helpers and review flow.

These tests stub external dependencies and interact with internal helpers to
validate behavior deterministically.
"""

# pylint: disable=missing-function-docstring, protected-access, too-few-public-methods,
# pylint: disable=unused-argument, import-error

import builtins
import pytest  # pylint: disable=import-error


# load_auto_detail fixture is provided by conftest.py; no import needed


def make_selector(return_values):
    """Create a stub inquirer.select/confirm factory.
    return_values can be a single value or an iterator of values to return from execute().
    """
    if not isinstance(return_values, (list, tuple)):
        it = iter([return_values])
    else:
        it = iter(return_values)

    class _Choice:
        def execute(self):
            return next(it)

    def _factory(*_args, **_kwargs):  # pylint: disable=unused-argument
        return _Choice()

    return _factory


def test_pretty_box_prints_basic_structure(capsys, load_auto_detail):
    mod = load_auto_detail
    mod._pretty_box()
    out = capsys.readouterr().out
    assert "Enter a reason for this PR" in out
    assert "Use #issue_num to reference issues" in out
    assert "(Leave blank to finish)" in out
    assert "╭" in out and "╯" in out


def test_get_pr_reasons_collects_until_blank(monkeypatch, load_auto_detail):
    mod = load_auto_detail
    inputs = iter(["Fix bug in parser", ""])  # stop on blank
    monkeypatch.setattr(builtins, "input", lambda *_args, **_kwargs: next(inputs))  # noqa: ARG002
    reasons = mod._get_pr_reasons("Initial reason")
    assert reasons == ["Initial reason", "Fix bug in parser"]


def test_confirm_clear_details_yes_calls_backend(monkeypatch, capsys, load_auto_detail):
    mod = load_auto_detail
    # Stub confirm to return True
    mod.inquirer.confirm = make_selector(True)
    called = {"cleared": False}
    mod.backend.clear_details = lambda: called.__setitem__("cleared", True)

    mod._confirm_clear_details()
    out = capsys.readouterr().out
    assert "Clearing details..." in out
    assert called["cleared"] is True


def test_confirm_clear_details_noop_on_no(monkeypatch, capsys, load_auto_detail):
    mod = load_auto_detail
    mod.inquirer.confirm = make_selector(False)
    called = {"cleared": False}
    mod.backend.clear_details = lambda: called.__setitem__("cleared", True)

    mod._confirm_clear_details()
    out = capsys.readouterr().out
    assert "Clearing details..." not in out
    assert called["cleared"] is False


def test_review_details_approve_path(monkeypatch, capsys, load_auto_detail):
    mod = load_auto_detail
    detail = {"summary": "S", "type": "feature", "description": "D"}
    # First action selection returns Approve
    mod.inquirer.select = make_selector(["Approve"])  # one and done

    called = {}

    def _write_note(desc, sum_, typ):
        called["args"] = (desc, sum_, typ)
        return "notes/foo.yaml"

    mod.backend.write_note = _write_note

    mod._review_details([detail], diff="dummy", pr_reasons=["R"])
    out = capsys.readouterr().out
    assert "Detail approved and written to file" in out
    assert called["args"] == ("D", "S", "feature")


def test_review_details_edit_ai_then_approve(monkeypatch, load_auto_detail):
    mod = load_auto_detail
    original = {"summary": "S", "type": "feature", "description": "D"}
    # Sequence: first choose edit with ai, then approve
    mod.inquirer.select = make_selector(["Edit detail with ai", "Approve"])

    def _edit_detail(diff, detail, pr_reasons, edit):
        assert edit  # user provided edit prompt
        return {"summary": "S2", "type": "bug", "description": "D2"}

    captured = {}
    mod.backend.edit_detail = _edit_detail

    def _write_note(desc, sum_, typ):
        captured["args"] = (desc, sum_, typ)
        return "notes/bar.yaml"

    mod.backend.write_note = _write_note

    # Provide input for the AI edit prompt
    monkeypatch.setattr(builtins, "input", lambda *_args, **_kwargs: "Tweak wording")

    mod._review_details([dict(original)], diff="diff", pr_reasons=["R"])  # copy
    assert captured["args"] == ("D2", "S2", "bug")


def test_review_details_edit_manual_then_approve(monkeypatch, load_auto_detail):
    mod = load_auto_detail
    d0 = {"summary": "S", "type": "feature", "description": "D"}

    # inquirer.select is used for action, then for type, then for action again
    # We will return: first -> "Edit detail manually", second -> "bug" (type), third -> "Approve"
    returns = ["Edit detail manually", "bug", "Approve"]
    mod.inquirer.select = make_selector(returns)

    # Inputs for summary and description during manual edit
    inputs = iter(["New summary", "New description"])
    monkeypatch.setattr(builtins, "input", lambda *_args, **_kwargs: next(inputs))

    captured = {}

    def _write_note(desc, sum_, typ):
        captured["args"] = (desc, sum_, typ)
        return "notes/baz.yaml"

    mod.backend.write_note = _write_note

    mod._review_details([dict(d0)], diff="diff", pr_reasons=["R"])  # work on a copy
    assert captured["args"] == ("New description", "New summary", "bug")


def test_review_details_restart_calls_main(monkeypatch, load_auto_detail):
    mod = load_auto_detail
    called = {"main": False}
    mod.main = lambda *a, **k: called.__setitem__("main", True)
    mod.inquirer.select = make_selector(["Restart"])  # triggers restart path

    # Should return early after calling main()
    mod._review_details(
        [{"summary": "s", "type": "t", "description": "d"}], "diff", ["r"]
    )
    assert called["main"] is True


def test_review_details_quit_exits(monkeypatch, load_auto_detail):
    mod = load_auto_detail
    mod.inquirer.select = make_selector(["Quit"])  # triggers sys.exit(0)

    with pytest.raises(SystemExit) as exc:
        mod._review_details(
            [{"summary": "s", "type": "t", "description": "d"}], "diff", ["r"]
        )
    assert exc.value.code == 0


def test_main_wires_components(monkeypatch, capsys, load_auto_detail):
    mod = load_auto_detail

    mod._get_pr_reasons = lambda reasons: ["r1", "r2"]
    mod._confirm_clear_details = lambda: None
    mod.backend.get_diff = lambda: "DIFF"
    called = {}

    def _gen(diff, reasons):
        called["generate"] = (diff, tuple(reasons))
        return [{"summary": "S", "type": "feature", "description": "D"}]

    mod.backend.generate_pr_details = _gen

    def _review(details, diff, pr_reasons):
        called["review"] = (tuple(details), diff, tuple(pr_reasons))

    mod._review_details = _review

    mod.main(reasons="initial")
    out = capsys.readouterr().out
    assert "Generating PR details..." in out
    assert called["generate"] == ("DIFF", ("r1", "r2"))
    assert called["review"][1] == "DIFF"


def test_new_command_calls_main(monkeypatch, load_auto_detail):
    mod = load_auto_detail
    called = {}
    mod.main = lambda reasons="": called.__setitem__("reasons", reasons)
    mod.new("abc reasons")
    assert called["reasons"] == "abc reasons"


def test_list_command_calls_backend_list_details(monkeypatch, load_auto_detail):
    mod = load_auto_detail
    called = {"listed": False}
    mod.backend.list_details = lambda: called.__setitem__("listed", True)
    mod.list_details()
    assert called["listed"] is True
