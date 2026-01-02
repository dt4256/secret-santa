import asyncio
import json
import os
import time
from aiogram.types import ReplyKeyboardRemove
from aiogram import Bot, Dispatcher, Router, F, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo,
    ReplyKeyboardMarkup, KeyboardButton
)
from aiogram.exceptions import TelegramForbiddenError

from config import ttkl
TOKEN = ttkl


bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

def add_user(user_id):
    try:
        with open("data/users.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        if user_id not in data:
            data.append(user_id) 
            os.mkdir(f"user_data/{user_id}")
            with open(f"user_data/{user_id}/preferences","w",encoding="utf-8") as f:
                #ТУТ ДОРАБАТЫВАТЬ ПРЕДПОЧТЕНИЯ ПРИ ИНИЦИАЛИЗАЦИИ
                tmp_preference={"permittions":"user","Name":"no_data","Second_name":"no_data","class":"0","numclass":"0"}
                json.dump(tmp_preference,f,ensure_ascii=False,indent=2)

            with open("data/users.json", "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            return "Initialised. Please, write /settings and configure your data. Program basicly will think that you are in London"
        else:
            return "already in"   
    except:
        return "smth gone wrong" 



@dp.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    t=add_user(user_id)
    print(t)
    await message.answer(t)
    print(message.from_user.id)

class GlobalInfoState(StatesGroup):
    waiting_for_text = State()

@router.message(Command("global_info"))
async def global_from_tg(message: Message, state: FSMContext):
    user_id = message.from_user.id
    try:
        with open(f"user_data/{user_id}/preferences", "r", encoding="utf-8") as f:
            prefs = json.load(f)
        if prefs.get("permittions") != "admin":
            await message.answer("You aren't admin")
            return
    except (FileNotFoundError, json.JSONDecodeError):
        await message.answer("Access denied or invalid preferences file.")
        return

    await message.answer("Enter global message")
    await state.set_state(GlobalInfoState.waiting_for_text)






@router.message(GlobalInfoState.waiting_for_text)
async def receive_global_text(message: Message, state: FSMContext, bot):
    msg = message.text
    if not msg:
        await message.answer("Empty message ignored.")
        await state.clear()
        return

    try:
        with open("data/users.json", "r", encoding="utf-8") as f:
            user_ids = json.load(f)
        if not isinstance(user_ids, list):
            await message.answer("Error: users.json must contain a JSON array of user IDs.")
            await state.clear()
            return
    except (FileNotFoundError, json.JSONDecodeError) as e:
        await message.answer(f"Failed to load user list: {e}")
        await state.clear()
        return

    sent_count = 0
    blocked_count = 0

    for uid in user_ids:
        try:
            await bot.send_message(chat_id=str(uid), text=msg)
            
        except TelegramForbiddenError:
            try:
                pref_path = f"user_data/{uid}/preferences"
                with open(pref_path, "r", encoding="utf-8") as pref_file:
                    data = json.load(pref_file)
                data["status"] = "blocked"
                with open(pref_path, "w", encoding="utf-8") as pref_file:
                    json.dump(data, pref_file, ensure_ascii=False, indent=2)
                
            except (FileNotFoundError, json.JSONDecodeError):
                await bot.send_message(chat_id=str(uid), text="smth wrong with your data. Please, send report about this problem")
                pass
        except Exception:
            #Telegram errors 
            pass

    await message.answer("sended")
    await state.clear()


class NameSettingsStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_surname = State()
    waiting_for_class = State()

@router.message(Command("profile_settings"))
async def profile_settings_menu(message: Message):
    user_id = str(message.from_user.id)
    prefs_path = f"user_data/{user_id}/preferences"
    
    try:
        with open(prefs_path, "r", encoding="utf-8") as f:
            prefs = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        await message.answer("Ошибка: файл настроек повреждён или не найден.")
        return

    name = prefs.get("Name") or "не задано"
    surname = prefs.get("Second_name") or "не задана"
    clas=str(prefs.get("class"))+"."+str(prefs.get("numclass"))

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Изменить имя", callback_data="edit_name")],
        [InlineKeyboardButton(text=f"Изменить фамилию", callback_data="edit_surname")],
        [InlineKeyboardButton(text=f"Изменить класс", callback_data="change_class")],
        [InlineKeyboardButton(text="Закрыть", callback_data="close_profile_menu")]
    ])
    await message.answer(f"Настройки профиля:\nАктуальное имя: {name}\nАктуальная фамилия: {surname}\nАктуальный класс: {clas}" , reply_markup=kb)


@router.callback_query(F.data=="change_class")
async def edit_class_start(callback: CallbackQuery,state: FSMContext):
    await callback.message.edit_text(f"Введите свой класс в формате\nКЛАСС.ПАРАЛЛЕЛЬ.\n Например 9.3")
    await state.set_state(NameSettingsStates.waiting_for_class)

@router.callback_query(F.data == "edit_name")
async def edit_name_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Введите новое имя:")
    await state.set_state(NameSettingsStates.waiting_for_name)
    await callback.answer()


@router.callback_query(F.data == "edit_surname")
async def edit_surname_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Введите новую фамилию:")
    await state.set_state(NameSettingsStates.waiting_for_surname)
    await callback.answer()


@router.message(NameSettingsStates.waiting_for_name)
async def save_name(message: Message, state: FSMContext):
    user_id = str(message.from_user.id)
    new_name = message.text.strip()

    try:
        with open(f"user_data/{user_id}/preferences", "r", encoding="utf-8") as f:
            prefs = json.load(f)
        prefs["Name"] = new_name
        with open(f"user_data/{user_id}/preferences", "w", encoding="utf-8") as f:
            json.dump(prefs, f, ensure_ascii=False, indent=2)
        await message.answer("Имя обновлено!")
    except Exception as e:
        await message.answer("Ошибка при сохранении имени.")
        print(f"Ошибка сохранения имени: {e}")

    await state.clear()
    await profile_settings_menu(message)


@router.message(NameSettingsStates.waiting_for_surname)
async def save_surname(message: Message, state: FSMContext):
    user_id = str(message.from_user.id)
    new_surname = message.text.strip()

    try:
        with open(f"user_data/{user_id}/preferences", "r", encoding="utf-8") as f:
            prefs = json.load(f)
        prefs["Second_name"] = new_surname
        with open(f"user_data/{user_id}/preferences", "w", encoding="utf-8") as f:
            json.dump(prefs, f, ensure_ascii=False, indent=2)
        await message.answer("Фамилия обновлена!")
    except Exception as e:
        await message.answer("Ошибка при сохранении фамилии.")
        print(f"Ошибка сохранения фамилии: {e}")

    await state.clear()
    await profile_settings_menu(message)

@router.message(NameSettingsStates.waiting_for_class)
async def save_class(message: Message, state: FSMContext):
    user_id = str(message.from_user.id)
    new_class = message.text.strip()

    try:
        with open(f"user_data/{user_id}/preferences", "r", encoding="utf-8") as f:
            prefs = json.load(f)
            if('.'not in new_class):
                await message.answer("Неправильный формат.")
                await state.clear()
                
                return

            temp = list(map(int, new_class.split('.')))#добавить на проверку букву
            if(temp[0]<1 or temp[0]>11) or (temp[1]<0 or temp[1]>6):
                await message.answer("Неправильный формат.")
                await state.clear()
                
                return
            else:
                prefs["class"]=temp[0]
                prefs["numclass"]=temp[1]
                with open(f"user_data/{user_id}/preferences", "w", encoding="utf-8") as f:
                    json.dump(prefs, f, ensure_ascii=False, indent=2)
                await message.answer("Класс обновлен")

    except Exception as e:
        await message.answer("Ошибка при сохранении класса.")
        print(f"Ошибка сохранения Класса: {e}")
    await state.clear()
    await profile_settings_menu(message)

@router.callback_query(F.data == "close_profile_menu")
async def close_profile_menu(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer()


async def main():
    await bot.send_message(chat_id="5130574101",text="Code is working")
    await dp.start_polling(bot)



if __name__ == "__main__":
    asyncio.run(main())