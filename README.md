# HTML Decoder Bot

## Button styles and Premium emoji

Copy `.env.example` to `.env` for local use, then set `BOT_TOKEN` and `OWNER_ID`.
On Railway or Render, add the same values as service environment variables.

Button colors use Telegram's three supported styles: `primary` (blue),
`success` (green), or `danger` (red). Set `BUTTON_STYLE_DECODE`,
`BUTTON_STYLE_DEVELOPER`, `BUTTON_STYLE_JOINED`, or `BUTTON_STYLE_CONTACT`.
Telegram does not accept arbitrary hex colors for bot buttons.

The supplied lightning emoji ID (`6057408307029613998`) is already mapped to
the decoder button and lightning symbols in messages. To add more Premium
custom emoji, set each numeric ID in the matching `BUTTON_EMOJI_*` variable
or `PREMIUM_EMOJI_*_ID`. Leave a value blank to use the regular emoji
fallback. Telegram requires the bot owner to have Premium or the bot to have
purchased additional usernames on Fragment.

The project uses `python-telegram-bot` 22.7 for Telegram Bot API 9.4 button
styles and custom emoji support.
