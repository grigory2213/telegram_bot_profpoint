import asyncio

from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text

from config import dp, bot, base, admins
from keyboards.client import send_message_kb

from states.client import *
from keyboards.admin import *

@dp.message_handler(commands=["sendmes"], user_id=admins, state="*")
async def send_mailing_wait_for_message(message: types.Message, state: FSMContext):
    await state.finish()
    await Mailing.get_text.set()
    async with state.proxy() as data:
        data['message_id'] = (await message.answer(
            "<b>❗Здравствуйте!</b>\n\n📨Пришлите сообщение для рассылки (Фото, текст, видео, голосовое сообщение):\n\n<em>Будьте осторожны, текст нужно вводить строго одним сообщением!</em>")).message_id
        print(await state.get_state())
        await asyncio.sleep(5)
        print(await state.get_state())
        if await state.get_state() == Mailing and 'type' not in (await state.get_data()).keys():
            await message.answer(123)

@dp.message_handler(state=Mailing.get_text, user_id=admins, content_types=types.ContentType.TEXT)
async def send_mailing_get_message(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['mailing'] = message.parse_entities()
        data['type'] = "text"
        await message.answer(message.parse_entities())
        data['message_id'] = (await message.answer("<b>❓Отправить?</b>", reply_markup=send_message_kb)).message_id
    await Mailing.get_choose.set()


@dp.message_handler(state=Mailing.get_text, user_id=admins, content_types=types.ContentType.PHOTO)
async def send_mailing_get_message(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['mailing'] = message.photo[0].file_id
        if message.parse_entities():
            data['caption'] = message.parse_entities()
            await message.answer_photo(data['mailing'], caption=data['caption'])
        else:
            await message.answer_photo(data['mailing'])
        data['type'] = "photo"
        data['message_id'] = (await message.answer("<b>❓Отправить?</b>", reply_markup=send_message_kb)).message_id
    await Mailing.get_choose.set()


@dp.message_handler(state=Mailing.get_text, user_id=admins, content_types=types.ContentType.VIDEO)
async def send_mailing_get_message(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['mailing'] = message.video.file_id
        if message.parse_entities():
            data['caption'] = message.parse_entities()
            await message.answer_video(data['mailing'], caption=data['caption'])
        else:
            await message.answer_video(data['mailing'])
        data['type'] = "video"
        data['message_id'] = (await message.answer("<b>❓Отправить?</b>", reply_markup=send_message_kb)).message_id
    await Mailing.get_choose.set()


@dp.message_handler(state=Mailing.get_text, user_id=admins, content_types=types.ContentType.VOICE)
async def send_mailing_get_message(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['mailing'] = message.voice.file_id
        if message.parse_entities():
            data['caption'] = message.parse_entities()
            await message.answer_voice(data['mailing'], caption=data['caption'])
        else:
            await message.answer_voice(data['mailing'])
        data['type'] = "voice"
        data['message_id'] = (
            await message.answer(f"<strong>❓Вы уверены в том, что хотите, чтобы это сообщение получило</strong>"
                                 f"<code> {len(await base.get_active_users())} пользователей</code>?",
                                 reply_markup=send_message_kb)).message_id
    await Mailing.get_choose.set()


@dp.callback_query_handler(Text("send_mailing"), state=Mailing.get_choose, user_id=admins)
async def send_mailing_accept(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        await call.message.edit_text("⏳ <strong>Рассылка началась ...</strong>")
        recieved_users, problem_users = 0, 0
        users = await base.get_active_users()
        for user in users:
            try:
                if data['type'] == "text":
                    await bot.send_message(user[0], data['mailing'])
                elif data['type'] == "photo":
                    if data['caption']:
                        await bot.send_photo(user[0], data['mailing'], caption=data['caption'])
                    else:
                        await bot.send_photo(user[0], data['mailing'])
                elif data['type'] == "video":
                    if data['caption']:
                        await bot.send_video(user[0], data['mailing'], caption=data['caption'])
                    else:
                        await bot.send_video(user[0], data['mailing'])
                elif data['type'] == "video":
                    if data['caption']:
                        await bot.send_voice(user[0], data['mailing'], caption=data['caption'])
                    else:
                        await bot.send_voice(user[0], data['mailing'])
                recieved_users += 1
            except:
                problem_users += 1
            finally:
                await asyncio.sleep(0.3)
    await call.message.edit_text(f"✉ <b>Рассылка окончена</b>\n\n"
                                 f"<strong>📊 Результат</strong>:\n"
                                 f"Сообщение успешно доставлено <code>{recieved_users}</code> пользователям ✔\n"
                                 f"Сообщение не было доставлено <code>{problem_users}</code> пользователям ❌")
    await state.finish()


@dp.callback_query_handler(Text("cancel_mailing"), user_id=admins, state=Mailing.get_choose)
async def send_mailing_cancel(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_text("✉ <strong>Рассылка успешно отменена ❌</strong>")
    await state.finish()