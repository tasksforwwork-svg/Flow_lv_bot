# ===== КНОПКА РЕДАКТИРОВАТЬ =====
@router.message(F.text == "✏️ Редактировать")
async def edit_button_handler(message: Message, state: FSMContext):
    from handlers.edit_transaction import edit_transaction
    await edit_transaction(message, state)
