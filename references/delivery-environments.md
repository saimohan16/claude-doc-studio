# Delivery environment details

Supplementary detail for the less-common branches of SKILL.md step 4 (Deliver
by environment) and step 8 (optional lavish-axi handoff). Read this file only
when the corresponding branch actually applies — most invocations won't need
either section.

## Claude.ai inline widget tool setup

When an inline HTML widget tool is available (e.g. a visualizer/show-widget
tool) and you're building with `--widget`:

- Follow the widget tool's own setup requirements before streaming the
  fragment — e.g. loading its read-me module first, if it has one.
- Stream the built fragment as the widget's content. It renders directly in
  the conversation with no download/open step.
- The app's Feedback drawer sends notes straight back into the chat via
  `sendPrompt` — no extra wiring needed on your side.
- Only additionally save/present the standalone `.html` if the user asks to
  keep, share, or open it outside the chat.

## lavish-axi live-review handoff (Claude Code only)

The built viewer is a standalone HTML artifact, so it also works with
[lavish-axi](https://github.com/kunchenguid/lavish-axi), a local
annotate-and-poll editor for HTML artifacts, as an alternative to the
built-in server + feedback queue (SKILL.md steps 4/6/7).

If the user has lavish-axi installed (or explicitly asks for a live review
loop outside the Doc Studio):

1. Open the built file: `npx -y lavish-axi <file>.studio.html`
2. Poll for annotations: `lavish-axi poll <file>.studio.html`
3. Act on returned annotations the same way as pasted Doc Studio feedback
   (SKILL.md step 7).
4. Stop polling on `status: ended`.

Never install or suggest lavish-axi unprompted — the built-in copy-paste
feedback queue (step 7) and live-review loop (step 6) are the default for
Claude Code.
