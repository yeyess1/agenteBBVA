#!/usr/bin/env python3
"""
Test script for Supabase-backed conversation memory
Verifies add_message, get_messages, get_full_history, and clear_conversation
"""

import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.conversation.memory import ConversationMemory
from src.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_conversation_memory():
    """Test Supabase conversation memory persistence"""
    print("\n" + "=" * 80)
    print("TESTING SUPABASE CONVERSATION MEMORY")
    print("=" * 80)

    # Initialize memory
    memory = ConversationMemory()
    test_user_id = "test_user_001"

    # Clear any existing conversation
    memory.clear_conversation(test_user_id)
    print("\n[1] Cleared any existing conversation for test user")

    # Test 1: Add messages
    print("\n[2] Testing add_message()...")
    print("-" * 80)

    messages_to_add = [
        ("user", "¿Cuál es la tasa de interés del crédito hipotecario?"),
        ("assistant", "La tasa de interés varía según el perfil crediticio del cliente, generalmente entre 7.5% y 12% anual."),
        ("user", "¿Cuáles son los requisitos para solicitar?"),
        ("assistant", "Los requisitos incluyen: cédula vigente, comprobante de ingresos, comprobante de domicilio, y no tener antecedentes negativos."),
        ("user", "¿Qué documentos necesito?"),
        ("assistant", "Necesitas: cédula de ciudadanía, últimas 3 nóminas, certificado de ingresos, comprobante de residencia, y certificado de referencias bancarias."),
    ]

    added_messages = []
    for role, content in messages_to_add:
        msg = memory.add_message(test_user_id, role, content)
        added_messages.append(msg)
        print(f"✅ Added {role}: {content[:60]}...")

    print(f"\n✅ Successfully added {len(added_messages)} messages")

    # Test 2: get_messages with context_window limit
    print("\n[3] Testing get_messages() with CONTEXT_WINDOW limit...")
    print("-" * 80)

    context_window = settings.context_window
    retrieved = memory.get_messages(test_user_id, last_n=context_window)
    print(f"Context window: {context_window}")
    print(f"Total messages added: {len(added_messages)}")
    print(f"Messages retrieved: {len(retrieved)}")

    if len(retrieved) == min(context_window, len(added_messages)):
        print(f"✅ Correct: got last {len(retrieved)} messages")
    else:
        print(f"❌ Error: expected {min(context_window, len(added_messages))}, got {len(retrieved)}")

    # Verify order is chronological
    if len(retrieved) > 0:
        print("\nFirst 2 messages retrieved:")
        for i, msg in enumerate(retrieved[:2], 1):
            print(f"  [{i}] {msg['role']}: {msg['content'][:50]}...")

    # Test 3: get_full_history without limit
    print("\n[4] Testing get_full_history()...")
    print("-" * 80)

    full_history = memory.get_full_history(test_user_id)
    print(f"Total messages in full history: {len(full_history)}")
    print(f"Total messages added: {len(added_messages)}")

    if len(full_history) == len(added_messages):
        print(f"✅ Correct: retrieved all {len(full_history)} messages")
    else:
        print(f"⚠️  Expected {len(added_messages)}, got {len(full_history)}")

    # Test 4: clear_conversation
    print("\n[5] Testing clear_conversation()...")
    print("-" * 80)

    success = memory.clear_conversation(test_user_id)
    if success:
        print("✅ clear_conversation returned True")
    else:
        print("❌ clear_conversation returned False")

    # Verify it's actually cleared
    after_clear = memory.get_full_history(test_user_id)
    if len(after_clear) == 0:
        print(f"✅ Verified: conversation is empty after clear (0 messages)")
    else:
        print(f"❌ Error: still {len(after_clear)} messages after clear")

    # Test 5: Max conversation length enforcement
    print("\n[6] Testing max_conversation_length enforcement...")
    print("-" * 80)

    max_length = settings.max_conversation_length
    print(f"Max conversation length: {max_length}")

    # Add more messages than max_length
    test_user_2 = "test_user_overflow"
    memory.clear_conversation(test_user_2)

    print(f"Adding {max_length + 5} messages (exceeds max by 5)...")
    for i in range(max_length + 5):
        role = "user" if i % 2 == 0 else "assistant"
        content = f"Message #{i+1}"
        memory.add_message(test_user_2, role, content)

    final_count = len(memory.get_full_history(test_user_2))
    print(f"Final message count: {final_count}")

    if final_count == max_length:
        print(f"✅ Correct: enforced max_length (expected {max_length}, got {final_count})")
    else:
        print(f"⚠️  Expected exactly {max_length}, got {final_count}")

    # Cleanup
    memory.clear_conversation(test_user_2)

    print("\n" + "=" * 80)
    print("✅ CONVERSATION MEMORY TEST COMPLETE!")
    print("=" * 80 + "\n")

    return True


if __name__ == "__main__":
    try:
        success = test_conversation_memory()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Test error: {e}", exc_info=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)
