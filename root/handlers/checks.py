import asyncio
from datetime import datetime

from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text

from config import dp, bot, base, admins

from keyboards.client import *
from states.client import *
from states.forms import *

@dp.message_handler(content_types=['location'])
async def get_free_checks(message: types.Message, state: FSMContext):
    user_longitude = message.location.longitude
    user_latitude = message.location.latitude
    longitude1 = user_longitude - 1.5
    longitude2 = user_longitude + 1.5
    latitude1 = user_latitude - 1.5
    latitude2 = user_latitude + 1.5
    checks = await base.get_available_checks(latitude1, longitude1, latitude2, longitude2)
    names = {"mts": "Салон связи", "sokolov": "Ювелирный магазин", "gate31": "Магазин одежды", "irbis": "АЗС",
             "kastorama": "Гипермаркет товаров для дома и строительства", "muztorg": "Магазин музыкальных инструментов",
             "subway": "Ресторан быстрого обслуживания", "ildebote": "Проверки магазинов косметики", "petshop": "Магазины зоотоваров", "rivgosh": "Магазины косметики",
             "torti": "Кондитерский магазин", "domix": "Магазин напольных покрытий", "informat": "Магазин канц. товаров", "lexmer": "Магазин мужской одежды", "respect": "Магазин обуви",
             "nebar": "Бар", "4paws": "Магазины зоотоваров"}
    if len(checks):
        await message.answer("📌<b>Список доступных проверок рядом с вами</b>", reply_markup=check_kb)
        for check in checks:
            await message.answer(f"<b>📎Номер проверки:</b> <code>{check[0]}</code>\n"
                                 f"<b>📍Адрес:</b> {check[1]}\n"
                                 f"<b>🈚Тип:</b> {names[check[3]]}\n"
                                 f"<b>💲Оплата:</b> {check[2]}", reply_markup=await get_detail_check_kb(check[3]))
            await asyncio.sleep(0.2)
    else:
        await message.answer("<b>❌К сожалению, на данный момент проверки рядом с вами не найдены</b>")

@dp.callback_query_handler(Text(startswith="show_"))
async def show_check_detail(call: types.CallbackQuery):
    details = {"kastorama": "Консультация по легенде в различных отделах, покупка от 40 рублей",
               "rivgosh": "Консультация по легенде + покупка от 200 рублей", "subway": "Оценка кафе быстрого питания, покупка сэндвича+ напитка за 320 рублей",
               "petshop": "Консультация по легенде+покупка на 600 рублей", "lexmer": "Консультация по легенде", "gate31": "Консультация по легенде, покупка-возврат",
               "respect": "Консультация по легенде с примеркой, покупка-возврат", "4paws": "Консультация по легенде + покупка от 150 рублей",
               "informat": "Консультация  по легенде с покупкой в магазине канцелярии", "torti": "Консультация по легенде",
               "domix": "Консультация по легенде", "nebar": "Визит в бар, заказ коктейля, оценка персонала",
               "pompa": "Консультация по легенде", "tissot": "Консультация по легенде с примеркой"}
    company = call.data.split("_")[1]
    await call.message.edit_text(call.message.text + f"\n\n📋Описание: <b>{details[company]}</b>")

@dp.message_handler(Text("📎Назначить проверку"))
async def appoint_check(message: types.Message, state: FSMContext):
    await message.answer("<b>🔢Введите номер проверки</b>", reply_markup=cancel_kb)
    await FSMassignation.number.set()

@dp.message_handler(state=FSMassignation.number)
async def get_appoint_number(message: types.Message, state: FSMContext):
    try:
        is_check_assignated = await base.assignate_check(message.from_user.id, int(message.text))
        if is_check_assignated:
            await message.answer(f"<b>✅Проверка под номером <code>{message.text}</code> успешно назначена</b>")
            company = await base.get_check_company(message.text)
            await message.answer_document(open(f'instructions/{company}.docx', 'rb'), caption="<b>📄Инструкция:</b>")
            await base.add_log(message.from_user.id, message.text, 'Назначил', company)
        else:
            await message.answer(f"<b>❌Проверка с таким номером не найдена или на неё назначен другой ТП</b>")
    except ValueError as e:
        await message.answer("<b>❌Ошибка: Номер проверки должен быть числом</b>")
        print(e)
    finally:
        await state.finish()

@dp.message_handler(Text("📄Мои проверки"))
async def get_user_checks(message: types.Message, state: FSMContext):
    user_checks = await base.get_user_checks(int(message.from_user.id))
    if len(user_checks):
        await message.answer("<b>📔Список ваших проверок:</b>", reply_markup=my_checks_kb)
        for check in user_checks:
            await message.answer(f"<b>📎Номер проверки:</b> <code>{check[0]}</code>\n"
                                 f"<b>📍Адрес:</b> {check[1]}\n", reply_markup=await get_cancel_check_kb(check[0]))
    else:
        await message.answer("<b>❌На данный момент у вас нет проверок</b>")

@dp.callback_query_handler(Text(startswith="uncheck_"))
async def cancel_check(call: types.CallbackQuery):
    check_id = call.data.split("_")[1]
    await base.cancel_check(check_id)
    await call.message.edit_text("✅Проверка отменена")
    company = await base.get_check_company(check_id)
    await base.add_log(call.from_user.id, check_id, 'Отменил', company)

@dp.message_handler(Text("📋Заполнить анкету"))
async def fill_form(message: types.Message, state: FSMContext):
    await message.answer("<b>Напишите номер проверки</b>", reply_markup=cancel_kb)
    await FSMgetnumberofcheck.number.set()

@dp.message_handler(state=FSMgetnumberofcheck.number)
async def get_number_of_check_to_fill(message: types.Message, state: FSMContext):
    companies_states = {"mts": FSMmts.date, "sokolov": FSMsokolov.date, "gate31": FSMgate31.date, "irbis": FSMirbis.date, "muztorg": FSMmuztorg.date,
                        "kastorama": FSMkastorama.date, "subway": FSMsubway.date, "torti": FSMtorti.info1, "domix": FSMdomix.info1, "informat": FSMinformat.info1,
                        "lexmer": FSMlexmer.info1}
    try:
        company = await base.is_user_have_check(message.from_user.id, int(message.text))
        await companies_states[company].set()
        async with state.proxy() as data_check:
            data_check['company'] = company
            data_check['user_id'] = message.from_user.id
            data_check['number'] = int(message.text)
            data_check['date_time'] = datetime.now()
        await message.answer("<b>Введите дату проверки</b>")
        await asyncio.sleep(300)
        if 'date' not in (await state.get_data()).keys():
            await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")
    except ValueError:
        await message.answer("<b>❌Ошибка: Номер проверки должен быть числом!</b>")
        await state.finish()

@dp.message_handler(state=FSMsokolov.date)
async def getting_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['date'] = message.text
    await FSMsokolov.next()
    await message.answer('Время начала проверки. Формат 17:20')
    await asyncio.sleep(300)
    if await state.get_state() == FSMsokolov.time_start and 'time_start' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMsokolov.time_start)
async def getting_time_start(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['time_start'] = message.text
    await FSMsokolov.next()
    await message.answer('Пришлите аудиозапись визита')
    await asyncio.sleep(300)
    if await state.get_state() == FSMsokolov.audio and 'audio' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMsokolov.audio, content_types=types.ContentType.AUDIO)
async def getting_audio(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['audio'] = f'https://api.telegram.org/file/bot5794915534:AAHb-BgGHR5eE3szwUsNYuyPKQ1x4CJaZBY/{(await bot.get_file(message.audio.file_id))["file_path"]}'
    await FSMsokolov.next()
    await message.answer('ФИО сотрудника (Или описание внешности, если не удалось разглядеть бейдж)')
    await asyncio.sleep(300)
    if await state.get_state() == FSMsokolov.name_worker and 'worker_name' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMsokolov.name_worker)
async def getting_fio(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['worker_name'] = message.text
    await FSMsokolov.next()
    await message.answer("Точное количество продавцов в торговом зале в момент входа в магазин")
    await asyncio.sleep(300)
    if await state.get_state() == FSMsokolov.number_workers and 'worker_count' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMsokolov.number_workers)
async def getting_worker_count(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['worker_count'] = message.text
    await FSMsokolov.next()
    await message.answer("Количество посетителей (клиентов магазина) в торговом зале в момент входа в магазин")
    await asyncio.sleep(300)
    if await state.get_state() == FSMsokolov.number_clients and 'client_count' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMsokolov.number_clients)
async def getting_client_count(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['client_count'] = message.text
        data_check['edit_message_id'] = \
            (await message.answer("На момент посещения все сотрудники не заняты личными делами (не занимаются своим макияжем и не употребляют пищу)",
                                  reply_markup=grade_kb)).message_id
    await FSMsokolov.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMsokolov.worker_job and 'worker_job' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMsokolov.worker_job)
async def getting_worker_job(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['worker_job'] = call.data.split("_")[1]
        await call.message.edit_text("При обслуживании покупателей сотрудник использует специальную подложку для демонстрации ювелирных изделий", reply_markup=grade_kb)
    await FSMsokolov.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMsokolov.worker_substrate and 'worker_substrate' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMsokolov.worker_substrate)
async def getting_worker_substrate(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['worker_substrate'] = call.data.split("_")[1]
        await call.message.edit_text("Продавец был вовлечен в процесс обслуживания, хотел помочь, располагал к себе, "
                                     "демонстрировал доброжелательность, улыбался. Подробно расскажите о своих впечатлениях", reply_markup=grade_kb)
    await FSMsokolov.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMsokolov.worker_friendliness and 'worker_friendliness' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMsokolov.worker_friendliness)
async def getting_worker_friendliness(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['worker_friendliness'] = call.data.split("_")[1]
        await call.message.edit_text("По итогам визита сложилось впечатление гостеприимной атмосферы и высококлассного обслуживания. Подробно расскажите о своих впечатлениях", reply_markup=grade_kb)
    await FSMsokolov.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMsokolov.worker_service and 'worker_service' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMsokolov.worker_service)
async def getting_worker_service(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['worker_service'] = call.data.split("_")[1]
        await base.add_log(call.from_user.id, data_check['number'], 'Выполнил', "sokolov")
        await call.message.edit_text(f"Спасибо! Анкета {data_check['number']} - заполнена!")
    await base.add_check("sokolov", state)
    await state.finish()


@dp.message_handler(content_types=[types.ContentType.TEXT, types.ContentType.PHOTO], state=FSMsokolov.audio)
async def audio_loop(message: types.Message, state: FSMContext):
    message_id = (await message.answer("Неверный формат сообщения.\n\nПожалуйста, пришлите аудио")).message_id
    await asyncio.sleep(5)
    await bot.delete_message(message.from_user.id, message_id)

@dp.message_handler(state=FSMmts.date)
async def getting_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['date'] = message.text
    await FSMmts.next()
    await message.answer('Время начала проверки. Формат 17:20')
    await asyncio.sleep(300)
    if await state.get_state() == FSMmts.time_start and 'time_start' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMmts.time_start)
async def getting_time_start(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['time_start'] = message.text
    await FSMmts.next()
    await message.answer('Салон работал согласно режиму работы?')
    await asyncio.sleep(300)
    if await state.get_state() == FSMmts.rezgim and 'rezgim' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMmts.rezgim)
async def getting_rezgim(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['rezgim'] = message.text
    await FSMmts.next()
    await message.answer('Пришлите количество сотрудников, присутсвовавших во время визита')
    await asyncio.sleep(300)
    if await state.get_state() == FSMmts.number_workers and 'number_workers' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMmts.number_workers)
async def getting_number_workers(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['number_workers'] = int(message.text)
    await FSMmts.next()
    await message.answer('Пришлите количество клиентов, присутсвовавших во время визита')
    await asyncio.sleep(300)
    if await state.get_state() == FSMmts.number_clients and 'number_clients' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMmts.number_clients)
async def getting_number_clients(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['number_clients'] = int(message.text)
    await FSMmts.next()
    await message.answer(
        'Пришлите Имя и Должность сотрудника, который проводил консультацию. Если не помните - напишите: не помню. Формат: Иванов Иван Иванович, консультант')
    await asyncio.sleep(300)
    if await state.get_state() == FSMmts.name_worker and 'name_worker' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMmts.name_worker)
async def getting_name_worker(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['name_worker'] = message.text
    await FSMmts.next()
    await message.answer('Коротко опишите внешний вид сотрудника.')
    await asyncio.sleep(300)
    if await state.get_state() == FSMmts.describe_worker and 'describe_worker' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMmts.describe_worker)
async def getting_describe_worker(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['describe_worker'] = message.text
    await FSMmts.next()
    await message.answer('Напишите короткое резюме визита. Добавьте комментарии по желанию.')
    await asyncio.sleep(300)
    if await state.get_state() == FSMmts.resume and 'resume' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMmts.resume)
async def getting_resume(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['resume'] = message.text
    await FSMmts.next()
    await message.answer('Пришилите аудиозапись визита.')
    await asyncio.sleep(300)
    if await state.get_state() == FSMmts.audio and 'audio' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMmts.audio, content_types=types.ContentType.AUDIO)
async def getting_audio(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['audio'] = f'https://api.telegram.org/file/bot5794915534:AAHb-BgGHR5eE3szwUsNYuyPKQ1x4CJaZBY/{(await bot.get_file(message.audio.file_id))["file_path"]}'
    await FSMmts.next()
    await message.answer('Прикрепите фото фасада с первого ракурса.')
    await asyncio.sleep(300)
    if await state.get_state() == FSMmts.photo1 and 'photo1' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMmts.photo1, content_types=types.ContentType.PHOTO)
async def getting_photo1(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['photo1'] = f'https://api.telegram.org/file/bot5794915534:AAHb-BgGHR5eE3szwUsNYuyPKQ1x4CJaZBY/{(await bot.get_file(message.photo[-1].file_id))["file_path"]}'
    await FSMmts.next()
    await message.answer('Прикрепите фото фасада со второго ракурса.')
    await asyncio.sleep(300)
    if await state.get_state() == FSMmts.photo2 and 'photo2' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMmts.photo2, content_types=types.ContentType.PHOTO)
async def getting_photo2(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['photo2'] = f'https://api.telegram.org/file/bot5794915534:AAHb-BgGHR5eE3szwUsNYuyPKQ1x4CJaZBY/{(await bot.get_file(message.photo[-1].file_id))["file_path"]}'
        await base.add_log(message.from_user.id, data_check['number'], 'Выполнил', "mts")
    await base.add_check("mts", state)
    await message.answer(f'Спасибо! Анкета {data_check["number"]} -- заполнена!', reply_markup=main_kb)
    await state.finish()

@dp.message_handler(content_types=[types.ContentType.TEXT, types.ContentType.PHOTO], state=[FSMmts.photo2, FSMmts.photo1])
async def photo_loop(message: types.Message, state: FSMContext):
    message_id = (await message.answer("Неверный формат сообщения.\n\nПожалуйста, пришлите фото")).message_id
    await asyncio.sleep(5)
    await bot.delete_message(message.from_user.id, message_id)

@dp.message_handler(content_types=[types.ContentType.TEXT, types.ContentType.PHOTO], state=FSMmts.audio)
async def audio_loop(message: types.Message, state: FSMContext):
    message_id = (await message.answer("Неверный формат сообщения.\n\nПожалуйста, пришлите аудио")).message_id
    await asyncio.sleep(5)
    await bot.delete_message(message.from_user.id, message_id)

@dp.message_handler(state=FSMgate31.date)
async def getting_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['date'] = message.text
    await FSMgate31.next()
    await message.answer('Пришлите аудиозапись визита')
    await asyncio.sleep(300)
    if await state.get_state() == FSMgate31.audio and 'audio' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMgate31.audio, content_types=types.ContentType.AUDIO)
async def getting_audio(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['audio'] = f'https://api.telegram.org/file/bot5794915534:AAHb-BgGHR5eE3szwUsNYuyPKQ1x4CJaZBY/{(await bot.get_file(message.audio.file_id))["file_path"]}'
    await FSMgate31.next()
    await message.answer('Пришлите фото фасада')
    await asyncio.sleep(300)
    if await state.get_state() == FSMgate31.photo and 'photo' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMgate31.photo, content_types=types.ContentType.PHOTO)
async def getting_photo(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['photo'] = f'https://api.telegram.org/file/bot5794915534:AAHb-BgGHR5eE3szwUsNYuyPKQ1x4CJaZBY/{(await bot.get_file(message.photo[-1].file_id))["file_path"]}'
    await FSMgate31.next()
    await message.answer("ФИО консультанта (Или описание внешности, если не удалось разглядеть бейдж)")
    await asyncio.sleep(300)
    if await state.get_state() == FSMgate31.operator_name and 'operator_name' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMgate31.operator_name)
async def getting_operator_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['operator_name'] = message.text
    await FSMgate31.next()
    await message.answer("Оцените внешнее оформление: вывеску, входную группу, витрины, манекены, чистоту. Пожалуйста, опишите подробно, особенно если есть замечания")
    await asyncio.sleep(300)
    if await state.get_state() == FSMgate31.outside and 'outside' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMgate31.outside)
async def getting_outside(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['outside'] = message.text
    await FSMgate31.next()
    await message.answer("Оцените внутреннее оформление: Торговый зал, примерочные, освещение, чистоту. Пожалуйста, опишите подробно, особенно если есть замечания")
    if await state.get_state() == FSMgate31.inside and 'inside' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMgate31.inside)
async def getting_inside(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['inside'] = message.text
    await FSMgate31.next()
    await message.answer("Оцените внешний вид и поведение сотрудников. Пожалуйста, опишите подробно, особенно если есть замечания")
    await asyncio.sleep(300)
    if await state.get_state() == FSMgate31.describe_worker and 'describe_worker' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMgate31.describe_worker)
async def getting_describe_worker(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['describe_worker'] = message.text
    await message.answer("Товар имеет опрятный вид, имеются магнитные датчики безопасности")
    await FSMgate31.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMgate31.product_appearance and 'product_appearance' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMgate31.product_appearance)
async def getting_product_appearance(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['product_appearance'] = message.text
        await message.answer("В примерочной присутствует ложка для обуви и вешалка", reply_markup=grade_kb)
    await FSMgate31.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMgate31.spoon and 'spoon' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMgate31.spoon)
async def getting_spoon(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['spoon'] = message.text
        await message.answer("Укажите количество сотрудников в торговом зале")
    await FSMgate31.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMgate31.worker_count and 'worker_count' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMgate31.worker_count)
async def getting_worker_count(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['worker_count'] = message.text
        await message.answer("Укажите количество покупателей в торговом зале")
    await FSMgate31.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMgate31.client_count and 'client_count' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMgate31.client_count)
async def getting_client_count(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['client_count'] = message.text
        await message.answer("Консультант поприветствовал Вас с улыбкой", reply_markup=friendliess_kb)
    await FSMgate31.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMgate31.consultant_friendliess and 'consultant_friendliess' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMgate31.consultant_friendliess)
async def getting_consultant_friendliess(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['consultant_friendliess'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("Консультант проводил до примерочной ", reply_markup=friendliess_kb)
    await FSMgate31.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMgate31.consultant_fitting and 'consultant_fitting' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMgate31.consultant_fitting)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['consultant_fitting'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("Консультант сам отнес выбранные товары в примерочную", reply_markup=friendliess_kb)
    await FSMgate31.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMgate31.consultant_products and 'consultant_products' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMgate31.consultant_products)
async def getting_consultant_products(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['consultant_products'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("Консультант провел к кассовой зоне", reply_markup=friendliess_kb)
    await FSMgate31.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMgate31.consultant_cash and 'consultant_cash' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMgate31.consultant_cash)
async def getting_consultant_cash(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['consultant_cash'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Консультант дождался оплаты (для универмага "Цветной", ТРЦ "Авиапарк", ТЦ "МЕГА Теплый стан")', reply_markup=friendliess_kb)
    await FSMgate31.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMgate31.consultant_payment and 'consultant_payment' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMgate31.consultant_payment)
async def getting_consultant_payment(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['consultant_payment'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('В примерочной обслуживал тот же сотрудник, что проводил консультацию в торговом зале', reply_markup=friendliess_kb)
    await FSMgate31.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMgate31.consultant_same and 'consultant_same' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMgate31.consultant_same)
async def getting_consultant_same(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['consultant_same'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("Имя дежурного по примерочной ")
    await FSMgate31.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMgate31.duty_name and 'duty_name' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMgate31.duty_name)
async def getting_duty_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['duty_name'] = message.text
        await message.answer("Консультант/дежурный по примерочной проверил количество выбранных вещей до и после примерки", reply_markup=friendliess_kb)
    await FSMgate31.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMgate31.consultant_product_count and 'consultant_product_count' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMgate31.consultant_product_count)
async def getting_consultant_product_count(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['consultant_product_count'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Консультант/дежурный по примерочной находился в непосредственной близости от примерочной', reply_markup=friendliess_kb)
    await FSMgate31.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMgate31.consultant_closeness and 'consultant_closeness' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMgate31.consultant_closeness)
async def getting_consultant_closeness(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['consultant_closeness'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('ФИО кассира (Или описание внешности, если не удалось разглядеть бейдж)')
    await FSMgate31.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMgate31.cashier_name and 'cashier_name' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMgate31.cashier_name)
async def getting_cashier_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['cashier_name'] = message.text
        await message.answer("Кассир поприветствовал Вас с улыбкой", reply_markup=friendliess_kb)
    await FSMgate31.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMgate31.cashier_friendliess and 'cashier_friendliess' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMgate31.consultant_friendliess)
async def getting_cashier_friendliess(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['cashier_friendliess'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Кассир/консультант завернул покупку в кальку (упаковочную бумагу) и положил в пакет', reply_markup=friendliess_kb)
    await FSMgate31.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMgate31.cashier_paper and 'cashier_paper' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMgate31.cashier_paper)
async def getting_cashier_paper(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['cashier_paper'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Кассир/консультант передал пакет в руки, выйдя из-за кассы (не через кассовую стойку)', reply_markup=friendliess_kb)
    await FSMgate31.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMgate31.cashier_handed and 'cashier_handed' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMgate31.cashier_handed)
async def getting_cashier_handed(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['cashier_handed'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Оцените общее впечатление от посещения магазина', reply_markup=grade_kb)
    await FSMgate31.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMgate31.general_impression and 'general_impression' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMgate31.general_impression)
async def getting_general_impression(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['general_impression'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Оцените доброжелательность сотрудников', reply_markup=grade_kb)
    await FSMgate31.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMgate31.worker_friendliess and 'worker_friendliess' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMgate31.worker_friendliess)
async def getting_worker_friendliess(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['worker_friendliess'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Оцените активность и заинтересованность консультирующего сотрудника', reply_markup=grade_kb)
    await FSMgate31.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMgate31.consultant_activity and 'consultant_activity' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMgate31.consultant_activity)
async def getting_consultant_activity(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['consultant_activity'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Оцените компетентность консультирующего сотрудника', reply_markup=grade_kb)
    await FSMgate31.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMgate31.worker_competence and 'worker_competence' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMgate31.worker_competence)
async def getting_worker_competence(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['worker_competence'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Оцените настойчивость консультанта в предложении продукции', reply_markup=grade_kb)
    await FSMgate31.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMgate31.worker_persistence and 'worker_persistence' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMgate31.worker_persistence)
async def getting_worker_persistence(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['worker_persistence'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Оцените достаточно ли времени сотрудники уделили консультации и оформлению покупки', reply_markup=grade_kb)
    await FSMgate31.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMgate31.worker_time and 'worker_time' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMgate31.worker_time)
async def getting_worker_time(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['worker_time'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Если ли желание вернуться в магазин и совершить еще покупки?', reply_markup=friendliess_kb)
    await FSMgate31.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMgate31.return_desire and 'return_desire' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMgate31.return_desire)
async def getting_return_desire(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['return_desire'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('ФИО сотрудника, проводившего возврат (Или описание внешности, если не удалось разглядеть бейдж)')
    await FSMgate31.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMgate31.back_name and 'back_name' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMgate31.back_name)
async def getting_back_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['back_name'] = message.text
        await message.answer("Сотрудник поприветствовал Вас с улыбкой", reply_markup=friendliess_kb)
    await FSMgate31.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMgate31.back_friendliess and 'back_friendliess' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMgate31.back_friendliess)
async def getting_back_friendliess(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['back_friendliess'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Оцените общее впечатление от возврата')
    await FSMgate31.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMgate31.back_main and 'back_main' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMgate31.back_main)
async def getting_back_main(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['back_main'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer(f"Спасибо! Анкета {data_check['number']} - заполнена!")
        await base.add_log(call.from_user.id, data_check['number'], 'Выполнил', "gate31")
    await base.add_check("gate31", state)
    await state.finish()

@dp.message_handler(state=FSMgate31.photo, content_types=[types.ContentType.TEXT, types.ContentType.AUDIO])
async def photo_loop(message: types.Message, state: FSMContext):
    message_id = (await message.answer("Неверный формат сообщения.\n\nПожалуйста, пришлите фото")).message_id
    await asyncio.sleep(5)
    await bot.delete_message(message.from_user.id, message_id)

@dp.message_handler(state=FSMgate31.photo, content_types=[types.ContentType.TEXT, types.ContentType.PHOTO])
async def audio_loop(message: types.Message, state: FSMContext):
    message_id = (await message.answer("Неверный формат сообщения.\n\nПожалуйста, пришлите аудио")).message_id
    await asyncio.sleep(5)
    await bot.delete_message(message.from_user.id, message_id)

@dp.message_handler(state=FSMirbis.date)
async def getting_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['date'] = message.text
    await FSMirbis.next()
    await message.answer('Пришлите аудиозапись визита')
    await asyncio.sleep(300)
    if await state.get_state() == FSMirbis.audio and 'audio' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMirbis.audio, content_types=types.ContentType.AUDIO)
async def getting_audio(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['audio'] = f'https://api.telegram.org/file/bot5794915534:AAHb-BgGHR5eE3szwUsNYuyPKQ1x4CJaZBY/{(await bot.get_file(message.audio.file_id))["file_path"]}'
    await FSMirbis.next()
    await message.answer('Пришлите фото фасада')
    await asyncio.sleep(300)
    if await state.get_state() == FSMirbis.photo and 'photo' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMirbis.photo)
async def getting_photo(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['photo'] = f'https://api.telegram.org/file/bot5794915534:AAHb-BgGHR5eE3szwUsNYuyPKQ1x4CJaZBY/{(await bot.get_file(message.photo[-1].file_id))["file_path"]}'
    await FSMirbis.next()
    await message.answer("Имя оператора АЗС (Или описание внешности, если не удалось разглядеть бейдж)")
    await asyncio.sleep(300)
    if await state.get_state() == FSMirbis.operator_name and 'operator_name' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMirbis.operator_name)
async def getting_operator_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['operator_name'] = message.text
    await FSMirbis.next()
    await message.answer("Имя заправщика АЗС (Или описание внешности, если не удалось разглядеть бейдж)")
    await asyncio.sleep(300)
    if await state.get_state() == FSMirbis.azs_name and 'azs_name' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMirbis.azs_name)
async def getting_azs_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['azs_name'] = message.text
    await FSMirbis.next()
    await message.answer("Номер колонки")
    if await state.get_state() == FSMirbis.column and 'column' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMirbis.column)
async def getting_column(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['column'] = message.text
    await FSMirbis.next()
    await message.answer("Оцените территорию АЗС и торговый зал. Везде ли было чисто, всё ли исправно. Пожалуйста, опишите подробно, особенно если есть замечания")
    await asyncio.sleep(300)
    if await state.get_state() == FSMirbis.territory and 'territory' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMirbis.territory)
async def getting_territory(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['territory'] = message.text
    await message.answer("Туалет чистый, в туалете хороший запах, график уборни заполнен. Пожалуйста, опишите подробно, особенно если есть замечания")
    await FSMirbis.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMirbis.sanuzel and 'sanuzel' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMirbis.sanuzel)
async def getting_sanuzel(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['sanuzel'] = message.text
        await message.answer("Насколько Вы довольны обстановкой на объекте?", reply_markup=grade_kb)
    await FSMirbis.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMirbis.situation and 'situation' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMirbis.situation)
async def getting_situation(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['situation'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("Что бы Вы порекомендовали улучшить в обстановке на объекте?")
    await FSMirbis.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMirbis.object_tips and 'object_tips' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMirbis.object_tips)
async def getting_object_tips(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['object_tips'] = message.text
        await message.answer("Как Вы считаете, с какой проблемой обстановки на объекте компании нужно начать работать уже сейчас?")
    await FSMirbis.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMirbis.main_problem and 'main_problem' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMirbis.main_problem)
async def getting_main_problem(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['main_problem'] = message.text
        await message.answer("Оцените внешний вид и работу заправщика. Пожалуйста, опишите подробно, особенно если есть замечания")
    await FSMirbis.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMirbis.filler_job and 'filler_job' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMirbis.filler_job)
async def getting_filler_job(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['filler_job'] = message.text
        await message.answer("Насколько Вы довольны этапом заправки автомобиля?", reply_markup=grade_kb)
    await FSMirbis.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMirbis.fill and 'fill' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMirbis.fill)
async def getting_fill(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['fill'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("Что бы Вы порекомендовали улучшить при заправке автомобиля?")
    await FSMirbis.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMirbis.fill_tips and 'fill_tips' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMirbis.fill_tips)
async def getting_fill_tips(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['fill_tips'] = message.text
        await message.answer("Как Вы считаете, с какой проблемой на этапе заправки автомобиля компании нужно начать работать уже сейчас? ")
    await FSMirbis.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMirbis.fill_problem and 'fill_problem' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMirbis.fill_problem)
async def getting_fill_problem(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['fill_problem'] = message.text
        await message.answer("Оцените внешний вид и работу оператора-кассира. Пожалуйста, опишите подробно, особенно если есть замечания")
    await FSMirbis.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMirbis.cashier_appearance and 'cashier_appearance' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMirbis.cashier_appearance)
async def getting_cashier_appearance(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['cashier_appearance'] = message.text
        await message.answer("Насколько Вы довольны работой оператора-кассира?", reply_markup=grade_kb)
    await FSMirbis.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMirbis.cashier_job and 'cashier_job' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMirbis.cashier_job)
async def getting_cashier_job(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['cashier_job'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("Что бы Вы порекомендовали улучшить в работе оператора-кассира?")
    await FSMirbis.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMirbis.cashier_tips and 'cashier_tips' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMirbis.cashier_tips)
async def getting_cashier_tips(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['cashier_tips'] = message.text
        await message.answer("Как Вы считаете, с какой проблемой работы оператора-кассира компании нужно начать работать уже сейчас?")
    await FSMirbis.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMirbis.cashier_problem and 'cashies_problem' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMirbis.cashier_problem)
async def getting_cashier_problem(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['cashier_problem'] = message.text
        await message.answer(f"Спасибо! Анкета {data_check['number']} - заполнена!")
        await base.add_log(message.from_user.id, data_check['number'], 'Выполнил', "irbis")
    await base.add_check("irbis", state)
    await state.finish()

@dp.message_handler(state=FSMirbis.photo, content_types=[types.ContentType.AUDIO, types.ContentType.TEXT])
async def photo_loop(message: types.Message, state: FSMContext):
    message_id = (await message.answer("Неверный формат сообщения.\n\nПожалуйста, пришлите фото")).message_id
    await asyncio.sleep(5)
    await bot.delete_message(message.from_user.id, message_id)

@dp.message_handler(state=FSMirbis.photo, content_types=[types.ContentType.PHOTO, types.ContentType.TEXT])
async def audio_loop(message: types.Message, state: FSMContext):
    message_id = (await message.answer("Неверный формат сообщения.\n\nПожалуйста, пришлите аудио")).message_id
    await asyncio.sleep(5)
    await bot.delete_message(message.from_user.id, message_id)

@dp.message_handler(state=FSMmuztorg.date)
async def getting_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['date'] = message.text
    await FSMmuztorg.next()
    await message.answer('Время начала проверки. Формат 17:20')
    await asyncio.sleep(300)
    if await state.get_state() == FSMmuztorg.audio and 'audio' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMmuztorg.audio, content_types=types.ContentType.AUDIO)
async def getting_audio(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['audio'] = f'https://api.telegram.org/file/bot5794915534:AAHb-BgGHR5eE3szwUsNYuyPKQ1x4CJaZBY/{(await bot.get_file(message.audio.file_id))["file_path"]}'
    await FSMmuztorg.next()
    await message.answer('Пришлите фотографию фасада магазина')
    await asyncio.sleep(300)
    if await state.get_state() == FSMmuztorg.photo1 and 'photo1' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMmuztorg.photo1, content_types=types.ContentType.PHOTO)
async def getting_photo1(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['photo1'] = f'https://api.telegram.org/file/bot5794915534:AAHb-BgGHR5eE3szwUsNYuyPKQ1x4CJaZBY/{(await bot.get_file(message.photo[-1].file_id))["file_path"]}'
    await FSMmuztorg.next()
    await message.answer('Прикрепите фотографию нарушений')
    await asyncio.sleep(300)
    if await state.get_state() == FSMmuztorg.photo2 and 'photo2' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMmuztorg.photo2, content_types=types.ContentType.PHOTO)
async def getting_photo1(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['photo2'] = f'https://api.telegram.org/file/bot5794915534:AAHb-BgGHR5eE3szwUsNYuyPKQ1x4CJaZBY/{(await bot.get_file(message.photo[-1].file_id))["file_path"]}'
    await FSMmuztorg.next()
    await message.answer('Пришлите количество продавцов в магазине')
    await asyncio.sleep(300)
    if await state.get_state() == FSMmuztorg.worker_count and 'worker_count' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMmuztorg.worker_count)
async def getting_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['worker_count'] = message.text
    await FSMmuztorg.next()
    await message.answer('Пришлите количество клиентов в зале')
    await asyncio.sleep(300)
    if await state.get_state() == FSMmuztorg.client_count and 'client_count' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMmuztorg.client_count)
async def getting_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['client_count'] = message.text
    await FSMmuztorg.next()
    await message.answer('Напишите ваш пол')
    await asyncio.sleep(300)
    if await state.get_state() == FSMmuztorg.sex and 'sex' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMmuztorg.sex)
async def getting_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['sex'] = message.text
    await FSMmuztorg.next()
    await message.answer('Напишите ваш возраст')
    await asyncio.sleep(300)
    if await state.get_state() == FSMmuztorg.age and 'age' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMmuztorg.age)
async def getting_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['age'] = message.text
    await FSMmuztorg.next()
    await message.answer('Консультант подошел к Вам в течение 3 минут Вашего нахождения в его поле видимости?')
    await asyncio.sleep(300)
    if await state.get_state() == FSMmuztorg.worker_3_minute and 'worker_3_minute' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMmuztorg.worker_3_minute)
async def getting_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['worker_3_minute'] = message.text
    await FSMmuztorg.next()
    await message.answer('ФИО консультанта (Или описание внешности, если не удалось разглядеть бейдж)')
    await asyncio.sleep(300)
    if await state.get_state() == FSMmuztorg.worker_name and 'worker_name' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMmuztorg.worker_name)
async def getting_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['worker_name'] = message.text
    await FSMmuztorg.next()
    await message.answer('Внешний вид сотрудника соответствует стандартам?')
    await asyncio.sleep(300)
    if await state.get_state() == FSMmuztorg.worker_appearance and 'worker_appearance' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMmuztorg.worker_appearance)
async def getting_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['worker_appearance'] = message.text
    await FSMmuztorg.next()
    await message.answer('Внешний вид торгового зала соответствует стандартам?')
    await asyncio.sleep(300)
    if await state.get_state() == FSMmuztorg.hall_appearance and 'hall_appearance' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMmuztorg.hall_appearance)
async def getting_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['hall_appearance'] = message.text
    await FSMmuztorg.next()
    await message.answer('Консультант был приветлив и внимателен к Вам, как к клиенту?')
    await asyncio.sleep(300)
    if await state.get_state() == FSMmuztorg.consultant_friendly and 'consultant_friendly' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMmuztorg.consultant_friendly)
async def getting_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['consultant_friendly'] = message.text
    await FSMmuztorg.next()
    await message.answer('При отсутствии возможности провести консультацию самостоятельно консультант пригласил другого сотрудника и познакомил с Вами?')
    await asyncio.sleep(300)
    if await state.get_state() == FSMmuztorg.other_consultant and 'other_consultant' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMmuztorg.other_consultant)
async def getting_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['other_consultant'] = message.text
    await FSMmuztorg.next()
    await message.answer('Оцените общее впечатление от посещения магазина')
    await asyncio.sleep(300)
    if await state.get_state() == FSMmuztorg.general_impression and 'general_impression' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMmuztorg.general_impression)
async def getting_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['general_impression'] = message.text
    await FSMmuztorg.next()
    await message.answer('Оцените активность и заинтересованность консультирующего сотрудника')
    await asyncio.sleep(300)
    if await state.get_state() == FSMmuztorg.consultant_activity and 'consultant_activity' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMmuztorg.consultant_activity)
async def getting_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['consultant_activity'] = message.text
    await FSMmuztorg.next()
    await message.answer('Оцените компетентность консультирующего сотрудника')
    await asyncio.sleep(300)
    if await state.get_state() == FSMmuztorg.worker_competence and 'worker_competence' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMmuztorg.worker_competence)
async def getting_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['worker_competence'] = message.text
        await base.add_log(message.from_user.id, data_check['number'], 'Выполнил', "muztorg")
    await base.add_check("muztorg", state)
    await message.answer(f'Спасибо! Анкета {data_check["number"]} -- заполнена!', reply_markup=main_kb)
    await state.finish()

@dp.message_handler(content_types=[types.ContentType.TEXT, types.ContentType.PHOTO], state=[FSMmuztorg.photo2, FSMmuztorg.photo1])
async def photo_loop(message: types.Message, state: FSMContext):
    message_id = (await message.answer("Неверный формат сообщения.\n\nПожалуйста, пришлите фото")).message_id
    await asyncio.sleep(5)
    await bot.delete_message(message.from_user.id, message_id)

@dp.message_handler(content_types=[types.ContentType.TEXT, types.ContentType.PHOTO], state=FSMmuztorg.audio)
async def audio_loop(message: types.Message, state: FSMContext):
    message_id = (await message.answer("Неверный формат сообщения.\n\nПожалуйста, пришлите аудио")).message_id
    await asyncio.sleep(5)
    await bot.delete_message(message.from_user.id, message_id)

@dp.message_handler(state=FSMkastorama.date)
async def getting_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['date'] = message.text
    await FSMkastorama.next()
    await message.answer('Время начала проверки. Формат 17:20')
    await asyncio.sleep(300)
    if await state.get_state() == FSMkastorama.time and 'time' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMkastorama.time)
async def getting_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['time'] = message.text
    await FSMkastorama.next()
    await message.answer('Пришлите аудиозапись визита')
    await asyncio.sleep(300)
    if await state.get_state() == FSMkastorama.audio and 'audio' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMkastorama.audio, content_types=types.ContentType.AUDIO)
async def getting_audio(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['audio'] = f'https://api.telegram.org/file/bot5794915534:AAHb-BgGHR5eE3szwUsNYuyPKQ1x4CJaZBY/{(await bot.get_file(message.audio.file_id))["file_path"]}'
    await FSMmts.next()
    await message.answer('Прикрепите фото фасада')
    await asyncio.sleep(300)
    if await state.get_state() == FSMkastorama.photo and 'photo' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMkastorama.photo, content_types=types.ContentType.PHOTO)
async def getting_photo1(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['photo'] = f'https://api.telegram.org/file/bot5794915534:AAHb-BgGHR5eE3szwUsNYuyPKQ1x4CJaZBY/{(await bot.get_file(message.photo[-1].file_id))["file_path"]}'
    await FSMmts.next()
    await message.answer('Парковка чистая (нет мусора, нет тележек на парковочных местах, убрано от снега)', reply_markup=kastorama_kb)
    await asyncio.sleep(300)
    if await state.get_state() == FSMkastorama.parking_clear and 'parking_clear' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMkastorama.parking_clear)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['parking_clear'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("На парковке есть свободные места", reply_markup=kastorama_kb)
    await FSMkastorama.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMkastorama.parking_free and 'parking_free' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMkastorama.parking_free)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['parking_free'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("На входе доступны тележки всех видов", reply_markup=kastorama_kb)
    await FSMkastorama.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMkastorama.carts and 'carts' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMkastorama.carts)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['carts'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("В туалетах чисто", reply_markup=kastorama_kb)
    await FSMkastorama.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMkastorama.toilets_clear and 'toilets_clear' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMkastorama.toilets_clear)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['toilets_clear'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("Замки во всех туалетных кабинках целые", reply_markup=kastorama_kb)
    await FSMkastorama.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMkastorama.zamki and 'zamki' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMkastorama.zamki)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['zamki'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("Вся сантехника в рабочем состоянии", reply_markup=kastorama_kb)
    await FSMkastorama.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMkastorama.santehnika and 'santehnika' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMkastorama.santehnika)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['santehnika'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("Легко можно найти информацию о том, где оформить доставку и забрать интернет-заказы", reply_markup=kastorama_kb)
    await FSMkastorama.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMkastorama.info and 'info' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMkastorama.info)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("По главной аллее магазина можно свободно перемещаться с тележкой", reply_markup=kastorama_kb)
    await FSMkastorama.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMkastorama.cart_alley and 'cart_alley' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMkastorama.cart_alley)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['cart_alley'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("Пришлите № кассового узла", reply_markup=kastorama_kb)
    await FSMkastorama.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMkastorama.cash_number and 'cash_number' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMkastorama.cash_number)
async def getting_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['cash_number'] = message.text
    await FSMkastorama.next()
    await message.answer('ФИО кассира и описание внешности')
    await asyncio.sleep(300)
    if await state.get_state() == FSMkastorama.cashier_name and 'cashier_name' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMkastorama.cashier_name)
async def getting_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['cashier_name'] = message.text
    await FSMkastorama.next()
    await message.answer('Какой Вы по счету в очереди?')
    await asyncio.sleep(300)
    if await state.get_state() == FSMkastorama.queue_number and 'queue_number' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMkastorama.queue_number)
async def getting_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['queue_number'] = message.text
    await FSMkastorama.next()
    await message.answer('Засеките время с момента как Вы встали в очередь в кассу и до момента, когда кассир выдал Вам чек (мин.)')
    await asyncio.sleep(300)
    if await state.get_state() == FSMkastorama.queue_time and 'queue_time' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMkastorama.queue_time)
async def getting_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['queue_time'] = message.text
    await FSMkastorama.next()
    await message.answer('Внешний вид кассира соответствует установленным стандартам, бейдж присутствует, форма чистая, отглаженная. Если были нарушения, обязательно укажите')
    await asyncio.sleep(300)
    if await state.get_state() == FSMkastorama.cashier_appearance and 'cashier_appearance' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMkastorama.cashier_appearance)
async def getting_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['cashier_appearance'] = message.text
    await FSMkastorama.next()
    await message.answer('Работа с покупателем (Покупатель до Вас)')
    await asyncio.sleep(300)
    if await state.get_state() == FSMkastorama.worker_job_client and 'worker_job_client' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMkastorama.worker_job_client)
async def getting_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['worker_job_client'] = message.text
    await FSMkastorama.next()
    await message.answer('Кассир корректно просит покупателя предъявить к оплате весь выбранный товар, выложив его на кассовый прилавок (крупногабаритный товар осматривает непосредственно в тележке при помощи покупателя, корректно просит покупателя развернуть крупногабаритный товар штрих-кодом к кассиру)', reply_markup=kastorama_kb)
    await asyncio.sleep(300)
    if await state.get_state() == FSMkastorama.cashier_correctly and 'cashier_correctly' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMkastorama.cashier_correctly)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['cashier_correctly'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("Легко можно найти информацию о том, где оформить доставку и забрать интернет-заказы", reply_markup=kastorama_kb)
    await FSMkastorama.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMkastorama.cashier_barcode and 'cashier_barcode' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMkastorama.cashier_correctly)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['cashier_correctly'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("Кассир сканировал штрих-код товара ИЛИ ввел штрих-код товара вручную, в случае, когда сканер не сработал", reply_markup=kastorama_kb)
    await FSMkastorama.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMkastorama.cashier_barcode and 'cashier_barcode' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMkastorama.cashier_barcode)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['cashier_barcode'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("При получении наличных денег от покупателя, кассир проверяет их платежеспособность на детекторах купюр или проверяет купюры «на ощупь»", reply_markup=kastorama_kb)
    await FSMkastorama.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMkastorama.cashier_solvency and 'cashier_solvency' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMkastorama.cashier_solvency)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['cashier_solvency'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("Кассир выдал сдачу покупателю вместе с чеком", reply_markup=kastorama_kb)
    await FSMkastorama.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMkastorama.cashier_change and 'cashier_change' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMkastorama.cashier_change)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['cashier_change'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("Работа с покупателем (При обслуживании Вас)")
    await FSMkastorama.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMkastorama.cashier_job_user and 'cashier_job_user' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMkastorama.cashier_job_user)
async def getting_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['cashier_job_user'] = message.text
    await FSMkastorama.next()
    await message.answer('Кассир позитивно настроен, демонстрирует уверенность, доброжелательность, открытость', reply_markup=kastorama_kb)
    await asyncio.sleep(300)
    if await state.get_state() == FSMkastorama.cashier_positive and 'cashier_positive' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMkastorama.cashier_positive)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['cashier_change'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("Кассир демонстрирует готовность помочь покупателю при необходимости")
    await FSMkastorama.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMkastorama.cashier_help and 'cashier_help' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMkastorama.cashier_help)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['cashier_help'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("Улыбается естественно и доброжелательно ИЛИ доброжелательное выражение лица без явной наигранной улыбки")
    await FSMkastorama.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMkastorama.cashier_benevolence and 'cashier_benevolence' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMkastorama.cashier_help)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['cashier_benevolence'] = call.data.split("_")[1]
        await call.message.edit_text(f"Спасибо. Анкета - {data_check['number']} заполнена")
        await base.add_check("kastorama", data_check)
        await base.add_log(call.from_user.id, data_check['number'], "Выполнил", "kastorama")
    await state.finish()

@dp.message_handler(state=FSMsubway.date)
async def getting_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['date'] = message.text
    await FSMsubway.next()
    await message.answer('Время начала проверки. Формат 17:20')
    await asyncio.sleep(300)
    if await state.get_state() == FSMsubway.time and 'time' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMsubway.time)
async def getting_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['time'] = message.text
    await FSMsubway.next()
    await message.answer('Аудиозапись визита')
    await asyncio.sleep(300)
    if await state.get_state() == FSMsubway.audio and 'audio' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMsubway.audio, content_types=types.ContentType.AUDIO)
async def getting_audio(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['audio'] = f'https://api.telegram.org/file/bot5794915534:AAHb-BgGHR5eE3szwUsNYuyPKQ1x4CJaZBY/{(await bot.get_file(message.audio.file_id))["file_path"]}'
    await FSMsubway.next()
    await message.answer('Фото чека')
    await asyncio.sleep(300)
    if await state.get_state() == FSMsubway.photo1 and 'photo1' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMsubway.photo1, content_types=types.ContentType.PHOTO)
async def getting_photo1(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['photo1'] = f'https://api.telegram.org/file/bot5794915534:AAHb-BgGHR5eE3szwUsNYuyPKQ1x4CJaZBY/{(await bot.get_file(message.photo[-1].file_id))["file_path"]}'
    await FSMsubway.next()
    await message.answer('Фото нарушений, если они были')
    await asyncio.sleep(300)
    if await state.get_state() == FSMsubway.photo2 and 'photo2' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMsubway.photo2, content_types=types.ContentType.PHOTO)
async def getting_photo1(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['photo2'] = f'https://api.telegram.org/file/bot5794915534:AAHb-BgGHR5eE3szwUsNYuyPKQ1x4CJaZBY/{(await bot.get_file(message.photo[-1].file_id))["file_path"]}'
    await FSMsubway.next()
    await message.answer('Фото фасада')
    await asyncio.sleep(300)
    if await state.get_state() == FSMsubway.photo3 and 'photo3' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMsubway.photo3, content_types=types.ContentType.PHOTO)
async def getting_photo1(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['photo3'] = f'https://api.telegram.org/file/bot5794915534:AAHb-BgGHR5eE3szwUsNYuyPKQ1x4CJaZBY/{(await bot.get_file(message.photo[-1].file_id))["file_path"]}'
    await FSMsubway.next()
    await message.answer('Фото/скан часов работы ресторана с Яндекс карт и фото часов работы ресторана на фасаде здания/ТЦ')
    await asyncio.sleep(300)
    if await state.get_state() == FSMsubway.photo4 and 'photo4' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMsubway.photo4, content_types=types.ContentType.PHOTO)
async def getting_photo1(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['photo4'] = f'https://api.telegram.org/file/bot5794915534:AAHb-BgGHR5eE3szwUsNYuyPKQ1x4CJaZBY/{(await bot.get_file(message.photo[-1].file_id))["file_path"]}'
    await FSMsubway.next()
    await message.answer('Фото меню ресторана')
    await asyncio.sleep(300)
    if await state.get_state() == FSMsubway.photo5 and 'photo5' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMsubway.photo5, content_types=types.ContentType.PHOTO)
async def getting_photo1(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['photo5'] = f'https://api.telegram.org/file/bot5794915534:AAHb-BgGHR5eE3szwUsNYuyPKQ1x4CJaZBY/{(await bot.get_file(message.photo[-1].file_id))["file_path"]}'
    await FSMsubway.next()
    await message.answer('Фото зоны выкладки продуктов')
    await asyncio.sleep(300)
    if await state.get_state() == FSMsubway.photo6 and 'photo6' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMsubway.photo6, content_types=types.ContentType.PHOTO)
async def getting_photo1(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['photo6'] = f'https://api.telegram.org/file/bot5794915534:AAHb-BgGHR5eE3szwUsNYuyPKQ1x4CJaZBY/{(await bot.get_file(message.photo[-1].file_id))["file_path"]}'
    await FSMsubway.next()
    await message.answer('Сумма по чеку')
    await asyncio.sleep(300)
    if await state.get_state() == FSMsubway.info1 and 'info1' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMsubway.info1)
async def getting_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info1'] = message.text
    await FSMsubway.next()
    await message.answer('Укажите, пожалуйста, Ваш возраст')
    await asyncio.sleep(300)
    if await state.get_state() == FSMsubway.info2 and 'info2' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMsubway.info2)
async def getting_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info2'] = message.text
    await FSMsubway.next()
    await message.answer('Как часто Вы бываете в ресторанах Subway?')
    await asyncio.sleep(300)
    if await state.get_state() == FSMsubway.info3 and 'info3' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMsubway.info3)
async def getting_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info3'] = message.text
    await FSMsubway.next()
    await message.answer('Пользовались ли Вы Мобильным приложением Subway до визита в качестве Тайного гостя?')
    await asyncio.sleep(300)
    if await state.get_state() == FSMsubway.info4 and 'info4' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMsubway.info4)
async def getting_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info4'] = message.text
    await FSMsubway.next()
    await message.answer('Количество сотрудников в зоне приема заказа')
    await asyncio.sleep(300)
    if await state.get_state() == FSMsubway.info5 and 'info5' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMsubway.info5)
async def getting_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info5'] = message.text
    await FSMsubway.next()
    await message.answer('ФИО сотрудника, который вас обслуживал (Или описание внешности, если не удалось рассмотреть)')
    await asyncio.sleep(300)
    if await state.get_state() == FSMsubway.info6 and 'info6' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMsubway.info6)
async def getting_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info6'] = message.text
    await FSMsubway.next()
    await message.answer('Время ожидания в очереди (2 и более человек перед Вами), если она была. Укажите точное время ожидания в очереди в минутах.')
    await asyncio.sleep(300)
    if await state.get_state() == FSMsubway.info7 and 'info7' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMsubway.info7)
async def getting_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info7'] = message.text
    await FSMsubway.next()
    await message.answer('Время ожидания в очереди (2 и более человек перед Вами), если она была. Укажите точное время ожидания в очереди в минутах.')
    await asyncio.sleep(300)
    if await state.get_state() == FSMsubway.info8 and 'info8' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMsubway.info8)
async def getting_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info8'] = message.text
    await FSMsubway.next()
    await message.answer('Оцените вежливость и доброжелательность')
    await asyncio.sleep(300)
    if await state.get_state() == FSMsubway.info9 and 'info9' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMsubway.info9)
async def getting_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info9'] = message.text
    await FSMsubway.next()
    await message.answer('Оцените вежливость и доброжелательность')
    await asyncio.sleep(300)
    if await state.get_state() == FSMsubway.info10 and 'info10' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMsubway.info10)
async def getting_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info10'] = message.text
    await FSMsubway.next()
    await message.answer('Оцените компетентность персонала')
    await asyncio.sleep(300)
    if await state.get_state() == FSMsubway.info11 and 'info11' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMsubway.info11)
async def getting_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info11'] = message.text
    await FSMsubway.next()
    await message.answer('Оцените компетентность персонала')
    await asyncio.sleep(300)
    if await state.get_state() == FSMsubway.info12 and 'info12' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMsubway.info11)
async def getting_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info11'] = message.text
    await FSMsubway.next()
    await message.answer('Оцените скорость обслуживания')
    await asyncio.sleep(300)
    if await state.get_state() == FSMsubway.info12 and 'info12' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMsubway.info12)
async def getting_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info12'] = message.text
    await FSMsubway.next()
    await message.answer('Оцените скорость обслуживания')
    await asyncio.sleep(300)
    if await state.get_state() == FSMsubway.info13 and 'info13' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMsubway.info13)
async def getting_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info13'] = message.text
    await FSMsubway.next()
    await message.answer('Оцените скорость обслуживания')
    await asyncio.sleep(300)
    if await state.get_state() == FSMsubway.info14 and 'info14' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMsubway.info14)
async def getting_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info14'] = message.text
    await FSMsubway.next()
    await message.answer('Оцените активность, нацеленность на продажу')
    await asyncio.sleep(300)
    if await state.get_state() == FSMsubway.info15 and 'info15' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMsubway.info15)
async def getting_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info15'] = message.text
    await FSMsubway.next()
    await message.answer('Оцените интерьер (удобство и комфорт для покупателя)')
    await asyncio.sleep(300)
    if await state.get_state() == FSMsubway.info16 and 'info16' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMsubway.info16)
async def getting_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info16'] = message.text
    await FSMsubway.next()
    await message.answer('Стандарты чистоты в зале и в прилегающей территории были выполнены. Обязательно напишите нарушения, если они были')
    await asyncio.sleep(300)
    if await state.get_state() == FSMsubway.info17 and 'info17' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMsubway.info17)
async def getting_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info17'] = message.text
    await FSMsubway.next()
    await message.answer('Стандарты чистоты в зале и в прилегающей территории были выполнены. Обязательно напишите нарушения, если они были')
    await asyncio.sleep(300)
    if await state.get_state() == FSMsubway.info18 and 'info18' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMsubway.info18)
async def getting_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info18'] = message.text
    await FSMsubway.next()
    await message.answer('Стандарты чистоты в зале и в прилегающей территории были выполнены', reply_markup=kastorama_kb)
    await asyncio.sleep(300)
    if await state.get_state() == FSMsubway.info19 and 'info19' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMsubway.info19)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info19'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("Туалетная комната выглядела чисто и аккуратно, необходимые принадлежности и заполненный лист уборки (заполняемый на ежечасной основе) в наличии", reply_markup=kastorama_kb)
    await FSMsubway.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMsubway.info20 and 'info20' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMsubway.info20)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info20'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("Сотрудник приготовил заказ в полном соответствии с Вашими озвученными пожеланиями. В ходе заказа Вы можете отказаться от каких-то овощей, которые не едите (например, лук, оливки) или попросить добавить каких-то овощей побольше. Также Вы можете попросить к сэндвичу несколько видов соуса или уточнить, сколько соуса Вам бы хотелось добавить (побольше, или, наоборот, поменьше). Сотруднику необходимо внимательно слушать такие пожелания Гостя и готовить заказ согласно этим пожеланиям, уточняя, если необходимо, все ли сделано верно.", reply_markup=kastorama_kb)
    await FSMsubway.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMsubway.info21 and 'info21' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMsubway.info21)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info21'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("Сотрудник приготовил заказ в полном соответствии с Вашими озвученными пожеланиями. В ходе заказа Вы можете отказаться от каких-то овощей, которые не едите (например, лук, оливки) или попросить добавить каких-то овощей побольше. Также Вы можете попросить к сэндвичу несколько видов соуса или уточнить, сколько соуса Вам бы хотелось добавить (побольше, или, наоборот, поменьше). Сотруднику необходимо внимательно слушать такие пожелания Гостя и готовить заказ согласно этим пожеланиям, уточняя, если необходимо, все ли сделано верно.", reply_markup=kastorama_kb)
    await FSMsubway.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMsubway.info22 and 'info22' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMsubway.info21)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info21'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("Напишите, как было реализовано добавление первой порции сыра (2 треугольника)")
    await FSMsubway.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMsubway.info22 and 'info22' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMsubway.info22)
async def getting_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info22'] = message.text
    await FSMsubway.next()
    await message.answer('Кассир выдал Вам чек', reply_markup=kastorama_kb)
    await asyncio.sleep(300)
    if await state.get_state() == FSMsubway.info23 and 'info23' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMsubway.info23)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info23'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("Кассир выдал корректную сдачу, если вы расплачивались наличными", reply_markup=kastorama_kb)
    await FSMsubway.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMsubway.info24 and 'info24' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMsubway.info24)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info24'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("Перечень блюд и сумма, указанная в чеке, полностью соответствовали Вашему заказу", reply_markup=kastorama_kb)
    await FSMsubway.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMsubway.info25 and 'info25' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMsubway.info25)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info25'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("Кассир начислил баллы за сделанный заказ в мобильном приложении", reply_markup=kastorama_kb)
    await FSMsubway.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMsubway.info26 and 'info26' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMsubway.info26)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info26'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("Комментарий к блоку «Культура обслуживания». Опишите Ваши впечатления от процесса заказа и расчета. Что в работе сотрудников Вам понравилось, а что нет. Прокомментируйте все отрицательные ответы.")
    await FSMsubway.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMsubway.info27 and 'info27' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMsubway.info27)
async def getting_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info27'] = message.text
    await FSMsubway.next()
    await message.answer('Все продукты в зоне заказа (ингредиенты для сэндвичей) и десерты в кассовой зоне свежие, выложены аккуратно', reply_markup=kastorama_kb)
    await asyncio.sleep(300)
    if await state.get_state() == FSMsubway.info28 and 'info28' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMsubway.info28)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info28'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("В зоне приготовления заказа отсутствовали пустые контейнеры", reply_markup=kastorama_kb)
    await FSMsubway.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMsubway.info29 and 'info29' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMsubway.info29)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info29'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("Какой вид салата (капусты) был в зоне приготовления заказа в Овощной секции")
    await FSMsubway.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMsubway.info30 and 'info30' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMsubway.info30)
async def getting_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info30'] = message.text
    await FSMsubway.next()
    await message.answer('Были ли замечания к сэндвичу?')
    await asyncio.sleep(300)
    if await state.get_state() == FSMsubway.info31 and 'info31' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMsubway.info31)
async def getting_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info31'] = message.text
    await FSMsubway.next()
    await message.answer('Если вы заказывали сэндвич поджаренным, мясная начинка была хорошо прогретой', reply_markup=kastorama_kb)
    await asyncio.sleep(300)
    if await state.get_state() == FSMsubway.info32 and 'info32' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMsubway.info32)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info32'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("Вам понравился вкус и качество сэндвича и напитка, которые Вы заказали", reply_markup=kastorama_kb)
    await FSMsubway.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMsubway.info33 and 'info33' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMsubway.info33)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info33'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("Вам понравился вкус и качество сэндвича и напитка, которые Вы заказали", reply_markup=kastorama_kb)
    await FSMsubway.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMsubway.info34 and 'info34' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMsubway.info34)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info34'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("Внешний вид сотрудников был опрятным, одежда сотрудников чистая. Бейдж в наличии.", reply_markup=kastorama_kb)
    await FSMsubway.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMsubway.info35 and 'info35' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMsubway.info35)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info35'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("После работы на кассе или после того, как сотрудник вышел из зоны кухни, он помыл/продезинфицировал руки перед надеванием перчаток и приготовлением сэндвича", reply_markup=kastorama_kb)
    await FSMsubway.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMsubway.info36 and 'info36' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMsubway.info36)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info36'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("Часы работы ресторана на Яндекс Картах совпадают с часами работы, заявленными на таблице с часами работы на входе в ресторан", reply_markup=kastorama_kb)
    await FSMsubway.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMsubway.info37 and 'info37' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMsubway.info37)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info37'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("Вы хотели бы, чтобы в следующий раз Вас обслуживал тот же сотрудник?", reply_markup=kastorama_kb)
    await FSMsubway.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMsubway.info38 and 'info38' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMsubway.info38)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info38'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("Будете ли Вы посещать торговые точки данной сети в будущем в качестве обычного клиента?", reply_markup=kastorama_kb)
    await FSMsubway.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMsubway.info39 and 'info39' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMsubway.info39)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info39'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("Что заставит Вас посетить данную торговую точку снова?")
    await FSMsubway.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMsubway.info40 and 'info40' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMsubway.info40)
async def getting_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info40'] = message.text
    await FSMsubway.next()
    await message.answer('Почему вы бы могли решить не посещать данную торговую точку снова')
    await asyncio.sleep(300)
    if await state.get_state() == FSMsubway.info41 and 'info41' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMsubway.info41)
async def getting_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info41'] = message.text
    await FSMsubway.next()
    await message.answer('Насколько вероятно, что Вы порекомендуете данный ресторан быстрого питания друзьям или коллегам? (оцените по 10-балльной шкале)')
    await asyncio.sleep(300)
    if await state.get_state() == FSMsubway.info42 and 'info42' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMsubway.info42)
async def getting_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info42'] = message.text
    await FSMsubway.next()
    await message.answer('Насколько вероятно, что Вы порекомендуете данный ресторан быстрого питания друзьям или коллегам? (оцените по 10-балльной шкале)')
    await asyncio.sleep(300)
    if await state.get_state() == FSMsubway.info43 and 'info43' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMsubway.info43)
async def getting_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info42'] = message.text
        await message.answer(f"Спасибо. Анкета - {data_check['number']} заполнена")
        await base.add_check("subway", data_check)
        await base.add_log(message.from_user.id, data_check['number'], "Выполнил", "subway")


@dp.message_handler(state=FSMildebote.date)
async def getting_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['date'] = message.text
    await FSMildebote.next()
    await message.answer('Время начала проверки. Формат 17:20')
    await asyncio.sleep(300)
    if await state.get_state() == FSMildebote.time and 'time' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMildebote.time)
async def getting_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['time'] = message.text
    await FSMildebote.next()
    await message.answer('Аудиозапись визита')
    await asyncio.sleep(300)
    if await state.get_state() == FSMildebote.audio and 'audio' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMildebote.audio, content_types=types.ContentType.AUDIO)
async def getting_audio(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['audio'] = f'https://api.telegram.org/file/bot5794915534:AAHb-BgGHR5eE3szwUsNYuyPKQ1x4CJaZBY/{(await bot.get_file(message.audio.file_id))["file_path"]}'
    await FSMildebote.next()
    await message.answer('Подробное описание визита')
    await asyncio.sleep(300)
    if await state.get_state() == FSMildebote.info1 and 'info1' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMildebote.info1)
async def getting_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info1'] = message.text
    await FSMildebote.next()
    await message.answer('Когда Вы вошли в магазин, с Вами поздоровались ("Здравствуйте", "Добрый день", "Рады Вас видеть в нашем магазине")', reply_markup=kastorama_kb)
    await asyncio.sleep(300)
    if await state.get_state() == FSMildebote.info2 and 'info2' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMildebote.info2)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info2'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("Во время посещения сотрудники торгового зала были заняты рабочими процессами, а не личными (не разговаривали по мобильному телефону, друг с другом, не игнорировали клиентов)", reply_markup=kastorama_kb)
    await FSMildebote.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMildebote.info3 and 'info3' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMildebote.info3)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info3'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("Внешний вид сотрудника охраны в магазине: одежда черного цвета (футболка, или рубашка, или пиджак, брюки), чистая не мятая, бейдж, аккуратная причёска", reply_markup=kastorama_kb)
    await FSMildebote.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMildebote.info4 and 'info4' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMildebote.info4)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info4'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("Внешний вид сотрудника охраны в магазине: одежда черного цвета (футболка, или рубашка, или пиджак, брюки), чистая не мятая, бейдж, аккуратная причёска", reply_markup=kastorama_kb)
    await FSMildebote.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMildebote.info5 and 'info5' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMildebote.info5)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info5'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("Внутри магазина чисто и аккуратно", reply_markup=kastorama_kb)
    await FSMildebote.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMildebote.info6 and 'info6' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMildebote.info6)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info6'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("Полы, торговое оборудование, стеллажи, тестер стенды, тестеры чистые", reply_markup=kastorama_kb)
    await FSMildebote.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMildebote.info7 and 'info7' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMildebote.info7)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info7'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("Вся продукция аккуратно расставлена на полках", reply_markup=kastorama_kb)
    await FSMildebote.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMildebote.info8 and 'info8' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMildebote.info8)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info8'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("Присутствуют ценники на весь товар или прайс-листы", reply_markup=kastorama_kb)
    await FSMildebote.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMildebote.info9 and 'info9' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMildebote.info9)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info9'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("В магазине играет музыка", reply_markup=kastorama_kb)
    await FSMildebote.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMildebote.info10 and 'info10' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMildebote.info10)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info10'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("Сотрудник выглядел опрятно: одет по форме (футболка, брюки, любая обувь черного цвета). Одежда чистая, не мятая. Обувь чистая. Бейдж в наличии", reply_markup=kastorama_kb)
    await FSMildebote.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMildebote.info11 and 'info11' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMildebote.info11)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info11'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("Волосы чистые, волосы ниже плеч  должны быть убраны (хвост, пучок).", reply_markup=kastorama_kb)
    await FSMildebote.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMildebote.info12 and 'info12' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMildebote.info12)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info12'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("Маникюр - аккуратный, однотонный, (допускается  френч, пастельные тона, оттенки красного и бордового, без рисунков, без страз). Длина ногтей - не более 15 мм. ", reply_markup=kastorama_kb)
    await FSMildebote.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMildebote.info13 and 'info13' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMildebote.info13)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info13'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("Макияж (для девушек):\n1) Макияж: умеренный, в натуральной гамме, с акцентом на глаза и/или на губы.\n2) Макияж аккуратный: на лице нет следов осыпавшихся теней, туши, неаккуратно растушеванного тонального средства.", reply_markup=kastorama_kb)
    await FSMildebote.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMildebote.info14 and 'info14' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMildebote.info14)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info14'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("Сотрудник попрощался с Вами независимо от того, было ли выбрано средство для покупки или нет  или сказал вы можете к нему обратиться , если у вас появятся вопросы.", reply_markup=kastorama_kb)
    await FSMildebote.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMildebote.info15 and 'info15' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")


@dp.callback_query_handler(Text(startswith="grade_"), state=FSMildebote.info15)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info15'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("Оцените уровень профессионализма и компетентности консультанта.")
    await FSMildebote.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMildebote.info16 and 'info16' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMildebote.info16)
async def getting_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info16'] = message.text
    await FSMildebote.next()
    await message.answer('Кассир выглядел опрятно: одет по форме (футболка, брюки, любая обувь черного цвета). Одежда чистая, не мятая. Обувь чистая. Бейдж в наличии', reply_markup=kastorama_kb)
    await asyncio.sleep(300)
    if await state.get_state() == FSMsubway.info17 and 'info17' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMildebote.info17)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info17'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("Волосы чистые, волосы ниже плеч  должны быть убраны (хвост, пучок).", reply_markup=kastorama_kb)
    await FSMildebote.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMildebote.info18 and 'info18' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMildebote.info18)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info18'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("Маникюр - аккуратный, однотонный, (допускается  френч, пастельные тона, оттенки красного и бордового, без рисунков, без страз). Длина ногтей - не более 15 мм. ", reply_markup=kastorama_kb)
    await FSMildebote.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMildebote.info19 and 'info19' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMildebote.info19)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info19'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("Макияж (для девушек):\n1) Макияж: умеренный, в натуральной гамме, с акцентом на глаза и/или на губы.\n2) Макияж аккуратный: на лице нет следов осыпавшихся теней, туши, неаккуратно растушеванного тонального средства.", reply_markup=kastorama_kb)
    await FSMildebote.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMildebote.info20 and 'info20' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMildebote.info20)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info20'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("Макияж (для девушек):\n1) Макияж: умеренный, в натуральной гамме, с акцентом на глаза и/или на губы.\n2) Макияж аккуратный: на лице нет следов осыпавшихся теней, туши, неаккуратно растушеванного тонального средства.", reply_markup=kastorama_kb)
    await FSMildebote.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMildebote.info21 and 'info21' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMsubway.info20)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info20'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("Сотрудник попрощался с Вами независимо от того, было ли выбрано средство для покупки или нет  или сказал вы можете к нему обратиться , если у вас появятся вопросы.", reply_markup=kastorama_kb)
    await FSMsubway.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMsubway.info21 and 'info21' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMsubway.info21)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info21'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("Сотрудник приготовил заказ в полном соответствии с Вашими озвученными пожеланиями. В ходе заказа Вы можете отказаться от каких-то овощей, которые не едите (например, лук, оливки) или попросить добавить каких-то овощей побольше. Также Вы можете попросить к сэндвичу несколько видов соуса или уточнить, сколько соуса Вам бы хотелось добавить (побольше, или, наоборот, поменьше). Сотруднику необходимо внимательно слушать такие пожелания Гостя и готовить заказ согласно этим пожеланиям, уточняя, если необходимо, все ли сделано верно.", reply_markup=kastorama_kb)
    await FSMsubway.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMsubway.info22 and 'info22' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMsubway.info21)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info21'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("Напишите, как было реализовано добавление первой порции сыра (2 треугольника)")
    await FSMsubway.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMsubway.info22 and 'info22' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMsubway.info22)
async def getting_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info22'] = message.text
    await FSMsubway.next()
    await message.answer('Кассир выдал Вам чек', reply_markup=kastorama_kb)
    await asyncio.sleep(300)
    if await state.get_state() == FSMsubway.info23 and 'info23' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMsubway.info23)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info23'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("Кассир выдал корректную сдачу, если вы расплачивались наличными", reply_markup=kastorama_kb)
    await FSMsubway.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMsubway.info24 and 'info24' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMsubway.info24)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info24'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("Перечень блюд и сумма, указанная в чеке, полностью соответствовали Вашему заказу", reply_markup=kastorama_kb)
    await FSMsubway.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMsubway.info25 and 'info25' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMsubway.info25)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info25'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("Кассир начислил баллы за сделанный заказ в мобильном приложении", reply_markup=kastorama_kb)
    await FSMsubway.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMsubway.info26 and 'info26' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMsubway.info26)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info26'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("Комментарий к блоку «Культура обслуживания». Опишите Ваши впечатления от процесса заказа и расчета. Что в работе сотрудников Вам понравилось, а что нет. Прокомментируйте все отрицательные ответы.")
    await FSMsubway.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMsubway.info27 and 'info27' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMsubway.info27)
async def getting_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info27'] = message.text
    await FSMsubway.next()
    await message.answer('Все продукты в зоне заказа (ингредиенты для сэндвичей) и десерты в кассовой зоне свежие, выложены аккуратно', reply_markup=kastorama_kb)
    await asyncio.sleep(300)
    if await state.get_state() == FSMsubway.info28 and 'info28' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMsubway.info28)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info28'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("В зоне приготовления заказа отсутствовали пустые контейнеры", reply_markup=kastorama_kb)
    await FSMsubway.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMsubway.info29 and 'info29' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMsubway.info29)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info29'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("Какой вид салата (капусты) был в зоне приготовления заказа в Овощной секции")
    await FSMsubway.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMsubway.info30 and 'info30' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMsubway.info30)
async def getting_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info30'] = message.text
    await FSMsubway.next()
    await message.answer('Были ли замечания к сэндвичу?')
    await asyncio.sleep(300)
    if await state.get_state() == FSMsubway.info31 and 'info31' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMsubway.info31)
async def getting_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info31'] = message.text
    await FSMsubway.next()
    await message.answer('Если вы заказывали сэндвич поджаренным, мясная начинка была хорошо прогретой', reply_markup=kastorama_kb)
    await asyncio.sleep(300)
    if await state.get_state() == FSMsubway.info32 and 'info32' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMtorti.info1)
async def getting_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info1'] = message.text
    await FSMtorti.next()
    await message.answer("Аудиозапись визита")

@dp.message_handler(state=FSMtorti.info2, content_types=types.ContentType.AUDIO)
async def getting_audio(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info2'] = f'https://api.telegram.org/file/bot5794915534:AAHb-BgGHR5eE3szwUsNYuyPKQ1x4CJaZBY/{(await bot.get_file(message.audio.file_id))["file_path"]}'
    await FSMtorti.next()
    await message.answer('Пришлите фото')
    await asyncio.sleep(300)
    if await state.get_state() == FSMtorti.info3 and 'info3' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMtorti.info3, content_types=types.ContentType.PHOTO)
async def getting_audio(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info3'] = f'https://api.telegram.org/file/bot5794915534:AAHb-BgGHR5eE3szwUsNYuyPKQ1x4CJaZBY/{(await bot.get_file(message.photo[-1].file_id))["file_path"]}'
    await FSMtorti.next()
    await message.answer('Внешнее состояние торговой точки: Световая вывеска, реклама, входные двери, крыльцо - нет повреждений, всё чисто. Обязательно прокомментируйте если были нарушения', reply_markup=kastorama_kb)
    await asyncio.sleep(300)
    if await state.get_state() == FSMtorti.info4 and 'info4' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMtorti.info4)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info4'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("Внутреннее состояние торговой точки. Освещение, торговый зал, оборудование, уголок покупателя - нет повреждений, всё чисто, нет запаха", reply_markup=kastorama_kb)
    await FSMtorti.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMtorti.info5 and 'info5' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMtorti.info5)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info5'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("Внешний вид персонала: Сотрудник в форме, аккуратный внешний вид, волосы собраны, руки чистые", reply_markup=kastorama_kb)
    await FSMtorti.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMtorti.info6 and 'info6' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMtorti.info6)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info6'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("Сотрудники заняты выполнением функциональных обязанностей. не разговаривают по личному телефону, не пьют/не едят в торговом зале", reply_markup=kastorama_kb)
    await FSMtorti.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMtorti.info7 and 'info7' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMtorti.info7)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info7'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("Сотрудники в первую очередь обслуживают покупателей, затем занимаются выкладкой товара, приемом товара и тд", reply_markup=kastorama_kb)
    await FSMtorti.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMtorti.info8 and 'info8' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMtorti.info8)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info8'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("Сотрудники не сидят в присутствии покупателей, не опираются на оборудование, не принимают закрытые позы при общении с покупателями", reply_markup=kastorama_kb)
    await FSMtorti.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMtorti.info9 and 'info9' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMtorti.info9)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info9'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("Нет курящих сотрудников на улице в момент вашего появления", reply_markup=kastorama_kb)
    await FSMtorti.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMtorti.info10 and 'info10' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMtorti.info10)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info10'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("В случае, если сотрудник вел разгрузочные работы, вернулся с улицы или т.п, после завершения вымыл руки (протер влажной салфеткой) или одел перчатки", reply_markup=kastorama_kb)
    await FSMtorti.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMtorti.info11 and 'info11' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMtorti.info11)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info11'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Выкладка товара логичная, легко найти нужную группу товаров. Отсутствие пустых мест в витринах. Ценники присутствуют на всех товарах, актуальные. Отсутствуют мятые, "ручные" ценники.', reply_markup=kastorama_kb)
    await FSMtorti.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMtorti.info12 and 'info12' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMtorti.info12)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info12'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Сотрудники магазина здороваются с каждым вошедшим покупателем.', reply_markup=kastorama_kb)
    await FSMtorti.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMtorti.info13 and 'info13' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMtorti.info13)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info13'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Сотрудники устанавливают контакт с клиентом в течение 1-2 минут с момента появления в торговом зале', reply_markup=kastorama_kb)
    await FSMtorti.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMtorti.info14 and 'info14' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMtorti.info14)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info14'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('В случае, если сотрудник занят работой с другим клиентом, обращает внимание на вновь вошедшего покупателя и сообщает о готовности проконсультировать в ближайшее время', reply_markup=kastorama_kb)
    await FSMtorti.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMtorti.info15 and 'info15' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMtorti.info15)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info15'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Сотрудники магазина соблюдает стандарт - Предлагают покупателям с касс', reply_markup=kastorama_kb)
    await FSMtorti.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMtorti.info16 and 'info16' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMtorti.info16)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info16'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Работа на кассе оперативная. Не возникает трудностей (отсутствие размена и др)', reply_markup=kastorama_kb)
    await FSMtorti.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMtorti.info17 and 'info17' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMtorti.info17)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info17'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Акционный товар и новинки присутствуют в полном объёме. Выложены в торгововом зале.', reply_markup=kastorama_kb)
    await FSMtorti.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMtorti.info18 and 'info18' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMtorti.info18)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info18'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Персонал доводит информацию об акциях до всех покупателей, привлекает внимание клиентов . Предлагает акционный товар, подчёркивая выгоду покупки', reply_markup=kastorama_kb)
    await FSMtorti.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMtorti.info19 and 'info19' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMtorti.info19)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info19'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Исходя из Вашего впечатления о магазине, с какой вероятностью (от 0 до 10) Вы порекомендуете его своим близким и знакомым? Обязательно прокомментируйте подробно свой ответ')
    await FSMtorti.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMtorti.info20 and 'info20' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMtorti.info20)
async def add_check(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info20'] = message.text
        await base.add_log(message.from_user.id, data_check['number'], 'Выполнил', "torti")
    await base.add_check("torti", state)
    await message.answer(f'Спасибо! Анкета {data_check["number"]} -- заполнена!', reply_markup=main_kb)
    await state.finish()

@dp.message_handler(state=FSMdomix.info1)
async def getting_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info1'] = message.text
    await FSMdomix.next()
    await message.answer("Аудиозапись визита")

@dp.message_handler(state=FSMdomix.info2, content_types=types.ContentType.AUDIO)
async def getting_audio(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info2'] = f'https://api.telegram.org/file/bot5794915534:AAHb-BgGHR5eE3szwUsNYuyPKQ1x4CJaZBY/{(await bot.get_file(message.audio.file_id))["file_path"]}'
    await FSMdomix.next()
    await message.answer('Пришлите фото')
    await asyncio.sleep(300)
    if await state.get_state() == FSMdomix.info3 and 'info3' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMdomix.info3, content_types=types.ContentType.PHOTO)
async def getting_audio(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info3'] = f'https://api.telegram.org/file/bot5794915534:AAHb-BgGHR5eE3szwUsNYuyPKQ1x4CJaZBY/{(await bot.get_file(message.photo[-1].file_id))["file_path"]}'
    await FSMdomix.next()
    await message.answer('ФИО проверяемого сотрудника')
    await asyncio.sleep(300)
    if await state.get_state() == FSMdomix.info4 and 'info4' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMdomix.info4)
async def getting_consultant_fitting(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info4'] = message.text
        await message.answer("Опишите подробно и последовательно, как проходила проверка. Акцент делайте на том, что говорил и как вёл себя консультирующий сотрудник, как проявлялась его компентентность и заинтересованность в продаже.")
    await FSMdomix.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMdomix.info5 and 'info5' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMdomix.info5)
async def getting_consultant_fitting(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info5'] = message.text
        await message.answer("Состояние торгового зала: чисто, мусор отсутствует, товары распределены равномерно, можно пройти свободно с тележкой, везде есть ценники", reply_markup=kastorama_kb)
    await FSMdomix.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMdomix.info6 and 'info6' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMdomix.info6)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info6'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("Продавец с бейджем, форма по стандартам, чистая, выглаженная.", reply_markup=kastorama_kb)
    await FSMdomix.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMdomix.info7 and 'info7' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMdomix.info7)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info7'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("Был ли занят оцениваемый продавец?", reply_markup=kastorama_kb)
    await FSMdomix.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMdomix.info8 and 'info8' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMdomix.info8)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info8'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("Разложил на полу напольное покрытие, развернул обои, нарисовал плитку в Ceramic 3D. ", reply_markup=kastorama_kb)
    await FSMdomix.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMdomix.info9 and 'info9' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMdomix.info9)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info9'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("Рассказал о коллекции/предложил сравнить коллекции, если клиент выбрал 2-3 варианта", reply_markup=kastorama_kb)
    await FSMdomix.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMdomix.info10 and 'info10' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMdomix.info10)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info10'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer("Рассказал о трех характеристиках на языке выгоды", reply_markup=kastorama_kb)
    await FSMdomix.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMdomix.info11 and 'info11' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMdomix.info11)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info11'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Рассчитал стоимость материалов по запросу клиента', reply_markup=kastorama_kb)
    await FSMdomix.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMdomix.info12 and 'info12' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMdomix.info12)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info12'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Если вы совершили покупку, сотрудник мотивировал к дальнейшему сотрудничеству: дал визитку, рассказал о сайте, взял номер телефона', reply_markup=kastorama_kb)
    await FSMdomix.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMdomix.info13 and 'info13' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMdomix.info13)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info13'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Если вы не совершили покупку, сотрудник предложил и рассчитал максимальную скидку', reply_markup=kastorama_kb)
    await FSMdomix.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMdomix.info14 and 'info14' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMdomix.info14)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info14'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Если вы не совершили покупку, рассказал о гарантии лучшей цены', reply_markup=kastorama_kb)
    await FSMdomix.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMdomix.info15 and 'info15' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMdomix.info15)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info15'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Оцените вежливость и доброжелательность сотрудника. По шкале от 1 до 5, где 1 - грубый сотрудник, 5 - очень вежливый сотрудник', reply_markup=grade31_kb)
    await FSMdomix.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMdomix.info16 and 'info16' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMdomix.info16)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info16'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Оцените активность и заинтересованность сотрудника. По шкале от 1 до 5, где 1 - пассивный сотрудник, 5 - сотрудник, заинтересованный в продаже', reply_markup=grade31_kb)
    await FSMdomix.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMdomix.info17 and 'info17' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMdomix.info17)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info17'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Оцените компетентность сотрудника и качество предоставленной информации. По шкале от 1 до 5, где 1 - совершенно не компетентен, информация не получена или получена некорректная информация, 5 - сотрудник компетентен, информация полная, понятная и корректная', reply_markup=grade31_kb)
    await FSMdomix.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMdomix.info18 and 'info18' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMdomix.info18)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info18'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Оцените оперативность обслуживания. По шкале от 1 до 5, где 1 - очень медленное обсуживание, 5 - оперативное обслуживание', reply_markup=grade31_kb)
    await FSMdomix.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMdomix.info19 and 'info19' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMdomix.info19)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info19'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Оцените внешний вид сотрудника. По шкале от 1 до 5, где 1 - неопрятный сотрудник, одежда не соответсвует корпоративному стилю, 5 - сотрудник выглядит аккуратно, одет по форме')
    await FSMdomix.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMdomix.info20 and 'info20' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMdomix.info20)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info20'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await base.add_log(call.from_user.id, data_check['number'], 'Выполнил', "domix")
    await base.add_check("domix", state)
    await call.message.answer(f'Спасибо! Анкета {data_check["number"]} -- заполнена!', reply_markup=main_kb)
    await state.finish()

@dp.message_handler(state=FSMinformat.info1)
async def getting_info(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info1'] = message.text
        await message.answer("Аудиозапись визита")
    await FSMinformat.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMinformat.info2 and 'info2' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMinformat.info2, content_types=types.ContentType.AUDIO)
async def getting_audio(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info2'] = f'https://api.telegram.org/file/bot5794915534:AAHb-BgGHR5eE3szwUsNYuyPKQ1x4CJaZBY/{(await bot.get_file(message.audio.file_id))["file_path"]}'
    await FSMinformat.next()
    await message.answer('Фото чека')
    await asyncio.sleep(300)
    if await state.get_state() == FSMinformat.info3 and 'info3' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMinformat.info3, content_types=types.ContentType.PHOTO)
async def getting_photo1(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info3'] = f'https://api.telegram.org/file/bot5794915534:AAHb-BgGHR5eE3szwUsNYuyPKQ1x4CJaZBY/{(await bot.get_file(message.photo[-1].file_id))["file_path"]}'
    await FSMinformat.next()
    await message.answer('Фото фасада')
    await asyncio.sleep(300)
    if await state.get_state() == FSMinformat.info4 and 'info4' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMinformat.info4, content_types=types.ContentType.PHOTO)
async def getting_photo1(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info4'] = f'https://api.telegram.org/file/bot5794915534:AAHb-BgGHR5eE3szwUsNYuyPKQ1x4CJaZBY/{(await bot.get_file(message.photo[-1].file_id))["file_path"]}'
    await FSMinformat.next()
    await message.answer('Имя сотрудника и описание внешности')
    await asyncio.sleep(300)
    if await state.get_state() == FSMinformat.info5 and 'info5' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMinformat.info5)
async def getting_info(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info5'] = message.text
        await message.answer("Когда Вы вошли в магазин, с Вами поздоровался кто-либо из продавцов в течение 2-3 минут (если продавцы не заняты с другим покупателем)?\n Продавец доброжелательно улыбнулся Вам?\n Сотрудник предложил Вам помощь?")
    await FSMinformat.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMinformat.info6 and 'info6' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMinformat.info6)
async def getting_info(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info6'] = message.text
        await message.answer("Сотрудник смог предложить товар, который соответствовал Вашей потребности?", reply_markup=kastorama_kb)
    await FSMinformat.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMinformat.info7 and 'info7' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMinformat.info7)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info7'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('При презентации товара сотрудник снимает товар с витрины, держит его в руках или передает в руки покупателю?', reply_markup=kastorama_kb)
    await FSMinformat.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMinformat.info8 and 'info8' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMinformat.info8)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info8'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Сотрудник владеет информацией о товаре (не читает информацию с этикетки)?', reply_markup=kastorama_kb)
    await FSMinformat.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMinformat.info9 and 'info9' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMinformat.info9)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info9'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Кассир оперативно произвел расчет?', reply_markup=kastorama_kb)
    await FSMinformat.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMinformat.info10 and 'info10' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMinformat.info10)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info10'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Кассир выдал Вам чек?', reply_markup=kastorama_kb)
    await FSMinformat.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMinformat.info11 and 'info11' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMinformat.info11)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info11'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Персонал (кассир, продавец) поддерживал зрительный контакт на протяжении всего общения с Вами?', reply_markup=kastorama_kb)
    await FSMinformat.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMinformat.info12 and 'info12' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMinformat.info12)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info12'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Витрины хорошо освещены, все лампы горят?\nНа витрине и в торговом зале размещены актуальные рекламные материалы?\n Какие плакаты представлены?\nСоблюдена чистота на витрине (нет пыли, чистый пол, стекло без грязи и разводов, следов скотча)?')
    await FSMinformat.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMinformat.info13 and 'info13' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMinformat.info13)
async def getting_info(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info13'] = message.text
        await message.answer("Входная зона содержится в чистоте?\nТовар имеет привлекательный внешний вид (не порван, не имеет заломов, грязи, пыли и пр.)?\nНа всех товарах, который Вы рассматривали, присутствует ценник?\nЕсли на товар снижена цена, это легко можно понять по ценнику (ценник красного/желтого/оранжевого цвета с перечеркнутой ценой)?\nОборудование в торговом зале чистое, отсутствует пыль?\nНа оборудовании представлено оптимальное количество товара (нет слишком перегруженного и пустого оборудования)?\nОсвещение в торговом зале настроено, все лампы в исправном состоянии?")
    await FSMinformat.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMinformat.info14 and 'info14' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMinformat.info14)
async def getting_info(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info14'] = message.text
        await message.answer("Сотрудники выглядят опрятно?\nУ всех сотрудников, которых Вы видели, были бейджи с именем?\nВнешний вид сотрудников соответствует принятым стандартам?\nВсе сотрудники в торговом зале находятся в масках и перчатках?")
    await FSMinformat.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMinformat.info15 and 'info15' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMinformat.info15)
async def getting_info(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info15'] = message.text
        await message.answer("Сотрудники в торговом зале не занимаются посторонними делами, не разговаривают на личные темы, не разговаривают по телефону, не жуют жевательную резинку и пр.?\nСотрудники всегда находятся в поле зрения покупателей и готовы помочь?")
    await FSMinformat.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMinformat.info16 and 'info16' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMinformat.info16)
async def getting_info(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info16'] = message.text
        await message.answer("Порекомендуете ли Вы этот магазин своим друзьям/знакомым/родственникам? Оцените по шкале от 1 до 10, где 10 – максимальная оценка.")
    await FSMinformat.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMinformat.info17 and 'info17' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMinformat.info17)
async def getting_info(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info17'] = message.text
        await message.answer("Оцените, насколько доброжелательными выглядят сотрудники магазина? Оцените по шкале от 1 до 10, где 10 – максимальная оценка.")
    await FSMinformat.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMinformat.info18 and 'info18' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMinformat.info18)
async def getting_consultant_fitting(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info18'] = message.text
        await message.answer(f"Спасибо. Анкета - {data_check['number']} заполнена")
        await base.add_check("informat", data_check)
        await base.add_log(message.from_user.id, data_check['number'], "Выполнил", "informat")
    await state.finish()

@dp.message_handler(state=FSMlexmer.info1)
async def getting_info(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info1'] = message.text
        await message.answer("Время входа")
    await FSMlexmer.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMlexmer.info2 and 'info2' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMlexmer.info2)
async def getting_info(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info2'] = message.text
        await message.answer("Аудиозапись визита")
    await FSMlexmer.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMlexmer.info3 and 'info3' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMlexmer.info3, content_types=types.ContentType.AUDIO)
async def getting_audio(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info3'] = f'https://api.telegram.org/file/bot5794915534:AAHb-BgGHR5eE3szwUsNYuyPKQ1x4CJaZBY/{(await bot.get_file(message.audio.file_id))["file_path"]}'
    await FSMlexmer.next()
    await message.answer('Количество продавцов в магазине')
    await asyncio.sleep(300)
    if await state.get_state() == FSMlexmer.info4 and 'info4' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMlexmer.info4)
async def getting_info(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info4'] = message.text
        await message.answer("ФИО продавца-консультанта")
    await FSMlexmer.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMlexmer.info5 and 'info5' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMlexmer.info5)
async def getting_info(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info5'] = message.text
        await message.answer("Наличие у продавцов формы и бейджа", reply_markup=kastorama_kb)
    await FSMlexmer.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMlexmer.info6 and 'info6' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMlexmer.info6)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info6'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Сотрудники выглядят аккуратно, производят приятное впечатление', reply_markup=kastorama_kb)
    await FSMlexmer.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMlexmer.info7 and 'info7' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMlexmer.info7)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info7'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Сотрудники выглядят аккуратно, производят приятное впечатление', reply_markup=kastorama_kb)
    await FSMlexmer.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMlexmer.info8 and 'info8' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMlexmer.info8)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info8'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('За ресепшен (столом) не более одного человека.', reply_markup=kastorama_kb)
    await FSMlexmer.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMlexmer.info9 and 'info9' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMlexmer.info9)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info9'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Продавцы, не занятые с клиентами равномерно распределены по торговому залу', reply_markup=kastorama_kb)
    await FSMlexmer.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMlexmer.info10 and 'info10' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMlexmer.info10)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info10'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Недалеко от входа в магазин находится продавец, который встречает (приветствует) покупателей', reply_markup=kastorama_kb)
    await FSMlexmer.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMlexmer.info11 and 'info11' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMlexmer.info11)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info11'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('При появлении покупателя в магазине продавец приветствует его в течение первых 5-и секунд', reply_markup=kastorama_kb)
    await FSMlexmer.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMlexmer.info12 and 'info12' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMlexmer.info12)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info12'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('У продавца приветливое выражение лица, он улыбается, поза открытая', reply_markup=kastorama_kb)
    await FSMlexmer.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMlexmer.info13 and 'info13' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMlexmer.info13)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info13'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Продавец здоровается отчетливо, громко, приветливым тоном', reply_markup=kastorama_kb)
    await FSMlexmer.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMlexmer.info14 and 'info14' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMlexmer.info14)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info14'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Продавец подходит к покупателю, который остановился возле любого товара более чем на 15 секунд.', reply_markup=kastorama_kb)
    await FSMlexmer.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMlexmer.info15 and 'info15' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMlexmer.info15)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info15'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Продавец стоит напротив покупателя, справа или слева от него', reply_markup=kastorama_kb)
    await FSMlexmer.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMlexmer.info16 and 'info16' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMlexmer.info16)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info16'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Продавец демонстрировал товар таким образом: изделия, которые вывешены фронтально демонстрировал на месте, отворачивая полку, отгибая воротник и т.п.,сложенные вещи разворачивает) или держал вещь в руках.', reply_markup=kastorama_kb)
    await FSMlexmer.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMlexmer.info17 and 'info17' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMlexmer.info17)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info17'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Продавец наглядно показывал вам товар (например, продемонстрировал качество пошива или показал качество отделки)', reply_markup=kastorama_kb)
    await FSMlexmer.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMlexmer.info18 and 'info18' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMlexmer.info18)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info18'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Перед примеркой подготавливает изделия — снимает с вешалки, расстёгивает пуговицы, молнии.', reply_markup=kastorama_kb)
    await FSMlexmer.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMlexmer.info19 and 'info19' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMlexmer.info19)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info19'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Продавец спросил вас, комфортно ли вам, удобна ли посадка, нравится ли вам, как сидит модель.', reply_markup=kastorama_kb)
    await FSMlexmer.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMlexmer.info20 and 'info20' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMlexmer.info20)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info20'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Продавец предлагал/приносил вам дополнительные варианты с учетом результатов примерки.', reply_markup=kastorama_kb)
    await FSMlexmer.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMlexmer.info21 and 'info21' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMlexmer.info21)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info21'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Возникло ли у вас желание сделать покупку после беседы с сотрудниками?', reply_markup=grade31_kb)
    await FSMlexmer.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMlexmer.info22 and 'info22' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMlexmer.info22)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info22'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Понравилось ли обслуживание, посоветуете ли вы друзьям и знакомым прийти в данный магазин?', reply_markup=grade31_kb)
    await FSMlexmer.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMlexmer.info23 and 'info23' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMlexmer.info23)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info23'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Опишите, что Вам понравилось и что следовало бы изменить в данном магазине? Не менее 3х предложений.')
    await FSMlexmer.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMlexmer.info24 and 'info24' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMlexmer.info24)
async def getting_info(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info24'] = message.text
        await message.answer("Фото фасада")
    await FSMlexmer.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMlexmer.info25 and 'info25' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMlexmer.info25, content_types=types.ContentType.PHOTO)
async def getting_photo1(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info25'] = f'https://api.telegram.org/file/bot5794915534:AAHb-BgGHR5eE3szwUsNYuyPKQ1x4CJaZBY/{(await bot.get_file(message.photo[-1].file_id))["file_path"]}'
    await FSMlexmer.next()
    await message.answer('Фото нарушений')
    await asyncio.sleep(300)
    if await state.get_state() == FSMlexmer.info26 and 'info26' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.message_handler(state=FSMlexmer.info26, content_types=types.ContentType.PHOTO)
async def getting_photo1(message: types.Message, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info26'] = f'https://api.telegram.org/file/bot5794915534:AAHb-BgGHR5eE3szwUsNYuyPKQ1x4CJaZBY/{(await bot.get_file(message.photo[-1].file_id))["file_path"]}'
    await FSMlexmer.next()
    await message.answer('Территория около входа в магазин чистая (территория перед входом в магазин внутри торгового центра), отсутствуют мусор, грязь и явная пыль', reply_markup=kastorama_kb)
    await asyncio.sleep(300)
    if await state.get_state() == FSMlexmer.info27 and 'info27' not in (await state.get_data()).keys():
        await message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")


@dp.callback_query_handler(Text(startswith="grade_"), state=FSMlexmer.info27)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info27'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Вывеска - чистая и поддерживается в хорошем состоянии (нет пыли и следов грязи). Подсветка включена.', reply_markup=kastorama_kb)
    await FSMlexmer.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMlexmer.info28 and 'info28' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMlexmer.info28)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info28'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Витрины у входа и входные двери чистые и в хорошем состоянии (без следов пыли, клейкой ленты или отпечатков пальцев, нет никаких посторонних надписей)', reply_markup=kastorama_kb)
    await FSMlexmer.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMlexmer.info29 and 'info29' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMlexmer.info29)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info29'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('На входной группе магазина есть табличка с графиком работы магазина', reply_markup=kastorama_kb)
    await FSMlexmer.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMlexmer.info30 and 'info30' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMlexmer.info30)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info30'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Все манекены в витринах аккуратно одеты', reply_markup=kastorama_kb)
    await FSMlexmer.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMlexmer.info31 and 'info31' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMlexmer.info31)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info31'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('На каждый манекен в витрине оформлен ценник', reply_markup=kastorama_kb)
    await FSMlexmer.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMlexmer.info32 and 'info32' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMlexmer.info32)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info32'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Все лампы подсветки витрины исправны', reply_markup=kastorama_kb)
    await FSMlexmer.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMlexmer.info33 and 'info33' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMlexmer.info33)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info33'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('На антикражных воротах счетчики не закрыты посторонними предметами, манекенами, бумагой и т.д.', reply_markup=kastorama_kb)
    await FSMlexmer.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMlexmer.info34 and 'info34' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMlexmer.info34)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info34'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Витрина вызывает желание подойти к ней, рассмотреть модели, зайти в магазин', reply_markup=kastorama_kb)
    await FSMlexmer.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMlexmer.info35 and 'info35' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMlexmer.info35)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info35'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Пол чистый, на полу нет мусора', reply_markup=kastorama_kb)
    await FSMlexmer.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMlexmer.info36 and 'info36' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMlexmer.info36)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info36'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Полки и торговое оборудование чистые (нет пыли, подтеков, разводов)', reply_markup=kastorama_kb)
    await FSMlexmer.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMlexmer.info37 and 'info37' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMlexmer.info37)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info37'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Столы и ресепшн чистые без подтеков разводов', reply_markup=kastorama_kb)
    await FSMlexmer.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMlexmer.info38 and 'info38' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMlexmer.info38)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info38'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Зеркала в магазине безупречно чистые и в хорошем состоянии (большие настенные зеркала в зале и в примерочных)', reply_markup=kastorama_kb)
    await FSMlexmer.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMlexmer.info39 and 'info39' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMlexmer.info39)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info39'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Торговое оборудование магазина находится в исправном состоянии', reply_markup=kastorama_kb)
    await FSMlexmer.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMlexmer.info40 and 'info40' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMlexmer.info40)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info40'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('На рабочих местах сотрудников отсутствуют продукты питания, напитки, личные вещи', reply_markup=kastorama_kb)
    await FSMlexmer.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMlexmer.info41 and 'info41' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMlexmer.info41)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info41'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Мусорные корзины не на виду', reply_markup=kastorama_kb)
    await FSMlexmer.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMlexmer.info42 and 'info42' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMlexmer.info42)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info42'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Рекламные материалы аккуратно размещены', reply_markup=kastorama_kb)
    await FSMlexmer.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMlexmer.info43 and 'info43' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMlexmer.info43)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info43'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Включено всё потолочное освещение', reply_markup=kastorama_kb)
    await FSMlexmer.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMlexmer.info44 and 'info44' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMlexmer.info44)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info44'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Товар аккуратно размещен на оборудовании, пустоты отсутствуют', reply_markup=kastorama_kb)
    await FSMlexmer.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMlexmer.info45 and 'info45' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMlexmer.info45)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info45'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Ценники: наличие, соответствуют товару, не мятые, хорошо читаются', reply_markup=kastorama_kb)
    await FSMlexmer.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMlexmer.info46 and 'info46' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMlexmer.info46)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info46'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Вы можете свободно пройти по магазину, в проходах не стоят коробки и прочие предметы мешающие перемещению по залу', reply_markup=kastorama_kb)
    await FSMlexmer.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMlexmer.info47 and 'info47' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMlexmer.info47)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info47'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Магазин выглядит аккуратно, производит приятное впечатление', reply_markup=kastorama_kb)
    await FSMlexmer.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMlexmer.info48 and 'info48' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMlexmer.info48)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info48'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('В примерочных есть: пуфик, чистый коврик, крючки для сумок', reply_markup=kastorama_kb)
    await FSMlexmer.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMlexmer.info49 and 'info49' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMlexmer.info49)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info49'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Никто из сотрудников не принимал пищу в торговом зале', reply_markup=kastorama_kb)
    await FSMlexmer.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMlexmer.info50 and 'info50' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMlexmer.info50)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info50'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Никто из сотрудников не жевал жевательную резинку', reply_markup=kastorama_kb)
    await FSMlexmer.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMlexmer.info51 and 'info51' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMlexmer.info51)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info51'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Сотрудники не заняты посторонними делами, разговорами между собой, в т.ч. по телефону', reply_markup=kastorama_kb)
    await FSMlexmer.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMlexmer.info52 and 'info52' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMlexmer.info52)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info52'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Сотрудники не собираются в группы', reply_markup=kastorama_kb)
    await FSMlexmer.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMlexmer.info53 and 'info53' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMlexmer.info53)
async def getting_consultant_fitting(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info53'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await call.message.answer('Никто из сотрудников не облокачивался на торговое оборудование (ресепшен, вешала для товара)', reply_markup=kastorama_kb)
    await FSMlexmer.next()
    await asyncio.sleep(300)
    if await state.get_state() == FSMlexmer.info54 and 'info54' not in (await state.get_data()).keys():
        await call.message.answer("Вы тут? Возможно вы забыли продолжить заполнять анкету")

@dp.callback_query_handler(Text(startswith="grade_"), state=FSMlexmer.info54)
async def getting_date(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data_check:
        data_check['info54'] = call.data.split("_")[1]
        await call.message.edit_text(call.message.text + "\n\n<b>✅Оценено</b>")
        await base.add_log(call.from_user.id, data_check['number'], 'Выполнил', "lexmer")
    await base.add_check("lexmer", state)
    await call.message.answer(f'Спасибо! Анкета {data_check["number"]} -- заполнена!', reply_markup=main_kb)
    await state.finish()

