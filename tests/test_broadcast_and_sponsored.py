import pytest
from bot.services.sponsored import parse_sponsored_button_input, attach_sponsored_content
from bot.database import (
    init_db,
    register_group,
    get_active_groups,
    get_active_groups_count,
    update_sponsored_text,
    update_sponsored_button,
    get_sponsored_settings,
    clear_sponsored_text,
    clear_sponsored_button,
    create_broadcast,
    record_broadcast_recipient,
    finish_broadcast,
    get_broadcast_recipients
)

def test_parse_sponsored_button_input():
    # Test #red danger style
    res = parse_sponsored_button_input("#red Join the #1 OTC - t.me/Oncarts")
    assert res is not None
    style, text, url = res
    assert style == "danger"
    assert text == "Join the #1 OTC"
    assert url == "https://t.me/Oncarts"
    assert "t.me" not in text

    # Test #green success style with full https
    res = parse_sponsored_button_input("#green Support Group - https://t.me/mygroup")
    assert res is not None
    style, text, url = res
    assert style == "success"
    assert text == "Support Group"
    assert url == "https://t.me/mygroup"

    # Test #blue primary style
    res = parse_sponsored_button_input("#blue Official Channel - t.me/channel")
    assert res is not None
    style, text, url = res
    assert style == "primary"
    assert text == "Official Channel"
    assert url == "https://t.me/channel"

    # Test invalid inputs
    assert parse_sponsored_button_input("just random text") is None
    assert parse_sponsored_button_input("#red Only Title Without Link") is None

@pytest.mark.asyncio
async def test_sponsored_db_and_attachment():
    await init_db()

    # Clear first
    await clear_sponsored_text()
    await clear_sponsored_button()

    # Verify initially empty/disabled
    sp = await get_sponsored_settings()
    assert sp["text_enabled"] == 0
    assert sp["button_enabled"] == 0

    # Set text and button
    await update_sponsored_text("<b>Sponsored:</b> Best OTC exchange!", enabled=1)
    await update_sponsored_button("danger", "Trade Now", "https://t.me/Oncarts", enabled=1)

    sp = await get_sponsored_settings()
    assert sp["text_enabled"] == 1
    assert sp["button_enabled"] == 1
    assert sp["button_text"] == "Trade Now"

    # Test attach_sponsored_content
    base_text = "Here is Bitcoin's stats"
    caption, markup = await attach_sponsored_content(base_text)
    
    assert "<blockquote><b>Sponsored:</b> Best OTC exchange!</blockquote>" in caption
    assert markup is not None
    assert len(markup.inline_keyboard) == 1
    assert markup.inline_keyboard[0][0].text == "Trade Now"
    assert markup.inline_keyboard[0][0].url == "https://t.me/Oncarts"

    # Clean up
    await clear_sponsored_text()
    await clear_sponsored_button()

@pytest.mark.asyncio
async def test_group_and_broadcast_db():
    await init_db()

    # Test group tracking
    await register_group(-1001234567, "Crypto Whales Lounge", "cryptowhales")
    groups = await get_active_groups()
    assert any(g["id"] == -1001234567 for g in groups)
    count = await get_active_groups_count()
    assert count >= 1

    # Test broadcast flow
    bid = await create_broadcast(
        sender_id=8525701355,
        target_type="both",
        message_id=999,
        from_chat_id=8525701355,
        total_targets=1,
        started_at=1000.0
    )
    assert bid > 0

    await record_broadcast_recipient(
        broadcast_id=bid,
        target_id=-1001234567,
        target_name="Crypto Whales Lounge",
        target_username="cryptowhales",
        is_group=1,
        status="SUCCESS",
        error_msg=None,
        created_at=1001.0
    )

    await finish_broadcast(bid, success_count=1, failed_count=0, blocked_count=0, finished_at=1002.0)
    recipients = await get_broadcast_recipients(bid)
    assert len(recipients) == 1
    assert recipients[0]["status"] == "SUCCESS"
