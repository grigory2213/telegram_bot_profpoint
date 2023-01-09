import asyncio

from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text

from config import dp, bot, base, admins

from keyboards.client import *
from states.client import *

@dp.message_handler(state=FSMregistration.name)
async def getting_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['id'] = message.from_user.id
        data['name'] = message.text
    await FSMregistration.next()
    await message.answer('<b>Напишите свою фамилию</b>')
    await asyncio.sleep(300)
    if await state.get_state() == FSMregistration.surname and 'surname' not in (await state.get_data()).keys():
        await message.answer("Тук-тук, кажется вы прервались. Пожалуйста, продолжите регистрацию")

@dp.message_handler(state=FSMregistration.surname)
async def getting_surname(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['surname'] = message.text
    await FSMregistration.next()
    await message.answer('<b>Введите ваш EMAIL</b>')
    await asyncio.sleep(300)
    if await state.get_state() == FSMregistration.email and 'email' not in (await state.get_data()).keys():
        await message.answer("Тук-тук, кажется вы прервались. Пожалуйста, продолжите регистрацию")


@dp.message_handler(state=FSMregistration.email)
async def getting_email(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['email'] = message.text
    await message.answer("<b>Введите ваш номер телефона</b>")
    await FSMregistration.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMregistration.phone and 'phone' not in (await state.get_data()).keys():
        await message.answer("Тук-тук, кажется вы прервались. Пожалуйста, продолжите регистрацию")

@dp.message_handler(state=FSMregistration.phone)
async def getting_phone(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['phone'] = message.text
        data['telegram_name'] = message.from_user.full_name
    source_kb = InlineKeyboardMarkup(row_width=1)
    source_kb.add(InlineKeyboardButton(text="Анастасия Барабанова", callback_data="s_0"))
    source_kb.add(InlineKeyboardButton(text="Анна Глущенко", callback_data="s_1"))
    source_kb.add(InlineKeyboardButton(text="Батуро Ольга", callback_data="s_2"))
    source_kb.add(InlineKeyboardButton(text="Дарья Дербина", callback_data="s_3"))
    source_kb.add(InlineKeyboardButton(text="Дарья Пестова", callback_data="s_4"))
    source_kb.add(InlineKeyboardButton(text="Ева Никонорова", callback_data="s_5"))
    source_kb.add(InlineKeyboardButton(text="Екатерина Белокур", callback_data="s_6"))
    source_kb.add(InlineKeyboardButton(text="Екатерина Заболотникова", callback_data="s_7"))
    source_kb.add(InlineKeyboardButton(text="Елена Герменцова", callback_data="s_8"))
    source_kb.add(InlineKeyboardButton(text="Елизавета Шабалина", callback_data="s_9"))
    source_kb.add(InlineKeyboardButton(text="Ирина Борисенкова", callback_data="s_10"))
    source_kb.add(InlineKeyboardButton(text="Кожевникова Юлия", callback_data="s_11"))
    source_kb.add(InlineKeyboardButton(text="Кристина Зырянова", callback_data="s_12"))
    source_kb.add(InlineKeyboardButton(text="Лилия Бахтеева", callback_data="s_13"))
    source_kb.add(InlineKeyboardButton(text="Мария Большакова", callback_data="s_14"))
    source_kb.add(InlineKeyboardButton(text="Мария Вихрева", callback_data="s_15"))
    source_kb.add(InlineKeyboardButton(text="Рита Данцигер", callback_data="s_16"))
    source_kb.add(InlineKeyboardButton(text="София Казаросян", callback_data="s_17"))
    source_kb.add(InlineKeyboardButton(text="Софья Горина", callback_data="s_18"))
    await message.answer('От кого из наших сотрудников Вы узнали про чат-бот?', reply_markup=source_kb)
    await FSMregistration.next()

@dp.callback_query_handler(Text(startswith="s_"), state=FSMregistration.source)
async def finish_registration(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        num = call.data.split("_")[1]
        source_list = ["Анастасия Барабанова", "Анна Глущенко", "Батуро Ольга", "Дарья Дербина", "Дарья Пестова", "Ева Никонорова",
                       "Екатерина Белокур", "Екатерина Заболотникова", "Елена Герменцова", "Елизавета Шабалина", "Ирина Борисенкова",
                       "Кожевникова Юлия", "Кристина Зырянова", "Лилия Бахтеева", "Мария Большакова", "Мария Вихрева", "Рита Данцигер",
                       "София Казаросян", "Софья Горина"]
        data['source'] = source_list[int(num)]
    await call.message.answer("<b>Регистрация успешно завершена!</b>", reply_markup=main_kb)
    await call.message.delete()
    print((await state.get_data()).values())
    await base.add_user((await state.get_data()).values())


