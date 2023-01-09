from aiogram.dispatcher.filters.state import StatesGroup, State


class HelpFSM(StatesGroup):
    get_comment = State()
    get_answer = State()

class FSMregistration(StatesGroup):
    name = State()
    surname = State()
    email = State()
    phone = State()
    source = State()

class FSMassignation(StatesGroup):
    number = State()

class FSMgetnumberofcheck(StatesGroup):
    number = State()

class Mailing(StatesGroup):
    get_text = State()
    get_choose = State()