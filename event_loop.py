import asyncio
import threading

main_loop = asyncio.new_event_loop()

def start_loop():
    asyncio.set_event_loop(main_loop)
    main_loop.run_forever()

threading.Thread(target=start_loop, daemon=True).start()
