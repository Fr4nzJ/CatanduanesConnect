import sys
import traceback

try:
    import chatbot
except Exception:
    traceback.print_exc()
    print('IMPORT_FAIL')
    sys.exit(2)

resp = chatbot.get_response('Hello, test')
print('BOT_RESPONSE:', resp)
if resp and 'model' not in resp.lower():
    print('SMOKE_OK')
    sys.exit(0)
else:
    print('SMOKE_FAIL')
    sys.exit(1)
