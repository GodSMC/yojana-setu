import pytest
from bot.channels import TelegramAPIError
from bot.storage import Store
from bot.telegram_polling import process_update


def update(callback=True):
    message = {'chat': {'id': 123, 'type': 'private'}, 'text': 'pension'}
    if callback:
        return {'update_id': 42, 'callback_query': {'id': 'expired-callback', 'data': 'pension', 'message': message}}
    return {'update_id': 42, 'message': message}


def test_expired_callback_still_sends_reply(tmp_path):
    methods = []
    def call(token, method, payload):
        methods.append(method)
        if method == 'answerCallbackQuery':
            raise TelegramAPIError(method, 400)
    process_update('test', Store(tmp_path/'bot.db', 's'*32), update(), call)
    assert methods == ['answerCallbackQuery', 'sendMessage']


def test_blocked_recipient_does_not_stall_polling(tmp_path):
    def call(token, method, payload):
        raise TelegramAPIError(method, 403)
    process_update('test', Store(tmp_path/'bot.db', 's'*32), update(False), call)


def test_transient_delivery_failure_is_retried_without_reapplying_answer(tmp_path):
    store = Store(tmp_path/'bot.db', 's'*32)
    def fail(token, method, payload):
        raise TelegramAPIError(method, 429, 15)
    with pytest.raises(TelegramAPIError) as exc:
        process_update('test', store, update(False), fail)
    assert exc.value.retry_after == 15
    sent = []
    process_update('test', store, update(False), lambda t,m,p: sent.append(p))
    assert 'state or union territory' in sent[0]['text']


def test_offsets_survive_restart_and_are_scoped_to_bot(tmp_path):
    path = tmp_path/'bot.db'
    first = Store(path, 's'*32)
    first.set_offset(10, 43)
    second = Store(path, 's'*32)
    assert second.get_offset(10) == 43
    assert second.get_offset(11) == 0
