from run_hy8.models import TailwaterDefinition
from run_hy8.type_helpers import TailwaterType

try:
    tw = TailwaterDefinition()
    tw.type = TailwaterType.RECTANGULAR
    print("Successfully set tw.type (unexpected)")
    print(f"tw.tw_type is {tw.tw_type}")
except AttributeError as e:
    print(f"Caught expected AttributeError: {e}")
except Exception as e:
    print(f"Caught unexpected exception: {type(e).__name__}: {e}")
