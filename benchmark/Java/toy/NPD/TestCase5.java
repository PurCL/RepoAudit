public class TestCase5 {

    public static void main(String[] args) {
        System.out.println("Starting Null Pointer Exception Demo.");
        
        // Step 1: Create an object that is null via an inter-procedural call.
        Object obj = test5_createObject();

        try {
            // Step 2: Process the object which propagates the null value.
            test5_processObject(obj);
        } catch (NullPointerException e) {
            System.out.println("Caught a NullPointerException: " + e.getMessage());
        }
    }

    // Function that simulates object creation but returns null.
    private static Object test5_createObject() {
        System.out.println("createObject: Calling getNullObject...");
        return test5_getNullObject();
    }

    // Helper function that explicitly returns null.
    private static Object test5_getNullObject() {
        System.out.println("getNullObject: Returning null.");
        return null;
    }

    // Function that further propagates the object received.
    private static void test5_processObject(Object obj) {
        System.out.println("processObject: Received object, calling useObject...");
        test5_useObject(obj);
    }
    
    // Function that uses the object, causing a Null Pointer Exception if object is null.
    private static void test5_useObject(Object obj) {
        System.out.println("useObject: Attempting to call toString on the object...");
        // This line will throw a NullPointerException if obj is null.
        System.out.println("Object's toString(): " + obj.toString());
    }
}