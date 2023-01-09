import asyncio

from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text

from config import dp, bot, base, admins

from keyboards.client import *
from states.client import *

@dp.message_handler(Text(["📙Вернуться в меню", "/start"]), state="*")
async def start_message(message: types.Message, state: FSMContext):
    await state.finish()
    if await base.user_exists(message.from_user.id):
        await message.answer("<b>📒Главное меню</b>", reply_markup=main_kb)
    else:
        await message.answer("<b>Приветствуем вас в боте Profpoint!</b>\n\nВы можете присоединиться к нашей команде контроллеров клиентского сервиса и стать “тайным покупателем” компании Profpoint!", reply_markup=first_kb)

@dp.callback_query_handler(Text("joinyes"))
async def join_message(call: types.CallbackQuery):
    await call.message.edit_text("Знаете ли вы, кто такие “Тайные покупатели”, которые не вызывают подозрений и узнают правду о реальном клиентском сервисе?", reply_markup=start_kb)

@dp.callback_query_handler(Text("start_no"))
async def join_message(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_text("""“Тайный покупатель” - это специально подготовленный человек, смысл работы которого заключается в посещении магазинов, офисов и сервисных центров компаний под видом обычного посетителя.

Перед участием в проверке тайные покупатели проходят инструктаж. Они получают конкретную задачу и ряд вопросов, на которые и нужно дать ответ после посещения торговой точки. 

Затем тайный покупатель приходит под видом обычного клиента и консультируется с сотрудником по необходимому товару/услуге. Весь визит необходимо записать на диктофон. Это может быть и диктофон, который есть почти в каждом мобильном устройстве.

После визита тайный покупатель заполняет анкету и прикладывает необходимые материалы: аудиозапись, фотографии и т.д. За правильно и качественно заполненные отчеты начисляется оплата. Чем шире поставленная задача, тем выше плата за проверку.

Как стать тайным покупателем? Все просто! Необходимо зарегистрироваться и заполнить анкету. Готовы?""")
    await call.message.answer("<b>Напишите свое имя</b>")
    await FSMregistration.name.set()
    await asyncio.sleep(300)
    if await state.get_state() == FSMregistration.name and 'name' not in (await state.get_data()).keys():
        await call.message.answer("Тук-тук, кажется вы прервались. Пожалуйста, продолжите регистрацию")

@dp.callback_query_handler(Text("start_yes"))
async def start_registration(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_text("<b>Напишите свое имя</b>")
    await FSMregistration.name.set()
    await asyncio.sleep(300)
    if await state.get_state() == FSMregistration.name and 'name' not in (await state.get_data()).keys():
        await call.message.answer("Тук-тук, кажется вы прервались. Пожалуйста, продолжите регистрацию")

@dp.message_handler(Text("💸Оплата"))
async def payment_message(message: types.Message):
    await message.answer("""Оплата за все проверки прошлого месяца суммируется и подсчитывается к 15-му числу текущего месяца. Например, за все работы, которые вы выполнили в октябре, оплата будет подсчитана к 15-му ноября. 

15-го числа каждого месяца Вам на почту приходит письмо, в котором указана заработанная сумма за прошлый месяц. Срок выплат - в течение 40 рабочих дней с момента рассылки (с 15го числа). 

Оплата будет осуществляться трем категориям получателей:

«Самозанятый» на Qugo - дополнительный налог 6% уплачивается самостоятельно,

«Физическое лицо» на Solar Staff - оплата начисляется за вычетом 7%

ИП на Solar Staff – налог выплачивается самостоятельно в зависимости от системы налогооблажения ИП""")

@dp.callback_query_handler(Text("cancel"), state="*")
async def cancel_action(call: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await call.message.answer("<b>❌Действие отменено</b>")
    await call.message.delete()
