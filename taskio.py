import asyncio
import logging
import redis
from aiogram import types
from aiogram.bot import api
import aiogram.utils.markdown as md
from aiogram.types import ParseMode
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

API_TOKEN = 'SECRET TOKEN'

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Form(StatesGroup):
    menu = State() 
    setlist = State()
    list = State()
    additem = State()

@dp.message_handler(commands=['start'], state='*')
async def start_message(message: types.Message):
    await Form.menu.set()
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    albutton = types.KeyboardButton(text="/addlist")
    keyboard.add(albutton)
    await bot.send_message(message.chat.id, "Howdy, {}! I'm @TaskioBot, your personal assistant in the distribution of your time and tasks!".format(message.from_user.first_name))
    await bot.send_message(message.chat.id, "You are in menu. Type in '/help' to get the list of my commands, also enter '/addlist' to make the new list of your tasks", reply_markup=keyboard)
    
@dp.message_handler(commands=['menu'], state=Form.menu)
async def menucmd_dup(message):
    return await bot.send_message(message.chat.id, "You are already in menu")
    
@dp.message_handler(commands=['menu'], state='*')
async def menucmd(message):
    await Form.menu.set()
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    albutton = types.KeyboardButton(text="/addlist")
    keyboard.add(albutton)
    await bot.send_message(message.chat.id, "You are in menu. Type in '*/help*' to get the list of my commands, also enter '*/addlist*' to make the new list of your tasks", reply_markup=keyboard, parse_mode = "Markdown")
    
@dp.message_handler(state=Form.menu, commands=['help'])
async def helpcmd(message: types.Message):
    await bot.send_message(message.chat.id, "*Current state* \n/menu \n*Commands*\n/addlist - add a to-do list\n/show - show the current list\n/rmlist - remove the list\n/editlist - edit the to-do list", parse_mode="Markdown")

@dp.message_handler(state=Form.menu, commands=['addlist'])
async def namelist(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        if data.get('lists', None) is None:
            data['lists'] = dict()
        if data.get('current_list', None) is None:
            data['current_list'] = 0
        data['current_list'] += 1
        data['lists'][data['current_list']] = dict()
    await Form.setlist.set()
    await message.reply("Here we go! Created list with index = {}. Let's name your list.".format(data['current_list']))
    await message.reply("For example: *9th May, 2022*", parse_mode = "Markdown")

@dp.message_handler(state='*', commands='cancel')
@dp.message_handler(Text(equals='cancel', ignore_case=True), state='*')
async def cancel_handler(message: types.Message, state: FSMContext):
    """
    Allow user to cancel any action
    """
    current_state = await state.get_state()
    if current_state is None:
        return await bot.send_message(message.chat.id, "Wait, buddy. There's no any active commands")
    logging.info('Cancelling state %r', current_state)
    await state.finish()
    await message.reply("The current command has been cancelled. Anything else I can do for you? Send *'/help'* for a list of commands", reply_markup=types.ReplyKeyboardRemove(), parse_mode = "Markdown")


@dp.message_handler(state=Form.setlist)
async def process_namelist(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['lists'][data['current_list']]['name'] = message.text
    await Form.next()
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    abutton = types.KeyboardButton(text="/add")
    keyboard.add(abutton)
    await bot.send_message(message.chat.id, "Great name - '*{}*', fill the list by your tasks. Send '/add' to make the task in your current list".format(message.text), reply_markup=keyboard, parse_mode = "Markdown")
    
@dp.message_handler(commands=['add'], state=Form.list)
async def additem(message: types.Message, state: FSMContext):
    await Form.next()
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    abutton = types.KeyboardButton(text="/add")
    keyboard.add(abutton)
    await bot.send_message(message.chat.id, "Adding to list. Enter item:", reply_markup=keyboard)

@dp.message_handler(state=Form.additem)
async def additem(message: types.Message, state: FSMContext):
    logging.info(message.text)
    async with state.proxy() as data:
        size = len(data['lists'][data['current_list']])
        data['lists'][data['current_list']][size] = message.text
    await Form.list.set()
    await bot.send_message(message.chat.id, "Added to list #{}, item #{} = {}".format(data['current_list'], len(data['lists'][data['current_list']])-1, message.text, parse_mode = "Markdown"))

@dp.message_handler(state=Form.list, commands=['help'])
async def helpcmd(message: types.Message):
    await bot.send_message(message.chat.id, "*Current state* \n/list \n*Commands*\n/add - add a task\n/show - show the current list\n/showit - show the list of addded items\n/rmlist - remove the list\n/exit - finish bot", parse_mode="Markdown")

@dp.message_handler(commands=['showit'], state=Form.list)
async def process_show_command(message, state: FSMContext):
    cur_list = None
    async with state.proxy() as data:
        cur_list = data['lists'][data['current_list']]
#         keys = [x for x in cur_list.keys() if not isinstance(x, int)]
#         st = ''
#         for index in sorted(keys): 
#             if index != '':
#                 st = cur_list[index] + '\n'
#             else:
#                 await message.reply(message.chat.id, "There is an empty list")
    await bot.send_message(message.chat.id, cur_list)

@dp.message_handler(commands=['show'], state=Form.menu)
async def process_show_all_command(message, state: FSMContext):
    cur_list = None
    async with state.proxy() as data:
        if data.get('lists', None) is None:
            return await bot.send_message(message.chat.id, "No lists")
        cur_list = data['lists']
    await bot.send_message(message.chat.id, cur_list)

@dp.message_handler(commands=['select'], state=Form.menu)
async def process_choose_command(message, state: FSMContext):
    cur_list = None
    async with state.proxy() as data:
        if data.get('lists', None) is None:
            return await bot.send_message(message.chat.id, "No lists")
        cur_list = data['lists']
        data['current_list'] = int(message.text[7:])
    await Form.list.set()
    await bot.send_message(message.chat.id, "Selected list #{}".format(int(message.text[7:])))
    await bot.send_message(message.chat.id, str(cur_list[int(message.text[7:])]))

@dp.message_handler(commands=['remove'], state=Form.list)
async def process_delete_command(message, state: FSMContext):
    cur_list = None
    async with state.proxy() as data:
        if data['lists'][data['current_list']].get(int(message.text[7:]), None) is None:
            return await bot.send_message(message.chat.id, "No such item")
        data['lists'][data['current_list']].pop(int(message.text[7:]))
        cur_list = data['lists'][data['current_list']]
    await bot.send_message(message.chat.id, str(cur_list))

@dp.message_handler(commands=['rmlist'], state=Form.menu)
async def process_rmlist_command(message, state: FSMContext):
    async with state.proxy() as data:
        if data['lists'].get(int(message.text[7:]), None) is None:
            return await bot.send_message(message.chat.id, "No such list")
        del_list = data['lists'].pop(int(message.text[7:]))
    await bot.send_message(message.chat.id, "List {} has been deleted".format(del_list), parse_mode="Markdown")

@dp.message_handler(commands=['selectit'], state=Form.list)
async def selectt(message, state: FSMContext):
    cur_item = None
    cur_list = None
    async with state.proxy() as data:
        # cur_list = data['lists'][data['current_list']]
        if data.get('lists', None) is None:
            return await bot.send_message(message.chat.id, "No lists")
        if data.get('current_list', None) is None:
            return await bot.send_message(message.chat.id, "No selected list")
        if data['lists'].get(data['current_list'], None) is None:
            return await bot.send_message(message.chat.id, "No item")
        cur_list = data['lists'][data['current_list']]
        if cur_list.get(int(message.text[9:]), None) is None:
            return await bot.send_message(message.chat.id, "No selected item")
        cur_item = cur_list[int(message.text[9:])]
        data['cur_item'] = int(message.text[9:])
        await bot.send_message(message.chat.id, "Selected item #{}".format(int(message.text[9:])))
        await bot.send_message(message.chat.id, str(cur_item), reply_markup = passbtn) 
        
passbtn = InlineKeyboardMarkup(row_width=1).add(InlineKeyboardButton(text = "Pass ✅", callback_data = 'pass'))

@dp.callback_query_handler(text='pass', state=Form.list)
async def operpass_call(callback: types.CallbackQuery):
    await callback.message.answer("Well Done! Keep it up, buddy! Send '/show' command to exit the task window")
    await callback.answer()

# @dp.callback_query_handler(text="operpass")
# @dp.message_handler(commands=['remove'], state=Form.list)
# async def process_delete_command(message, state: FSMContext):
#     cur_list = None
#     async with state.proxy() as data:
#         if data['lists'][data['current_list']].get(int(message.text[7:]), None) is None:
#             return await bot.send_message(message.chat.id, "No such item")
#         data['lists'][data['current_list']].pop(int(message.text[7:]))
#         cur_list = data['lists'][data['current_list']]
#     await bot.send_message(message.chat.id, str(cur_list))
    
@dp.message_handler(commands=['exit'], state='*')
async def exit_command(message: types.Message):
    await bot.send_message(message.chat.id, "Thanks for using @TaskioBot, {}! See you soon, little hero!".format(message.from_user.first_name))

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
