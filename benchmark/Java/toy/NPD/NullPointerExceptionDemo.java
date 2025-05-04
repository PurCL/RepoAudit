public class NullPointerExceptionDemo {

    public static void main(String[] args) {
        System.out.println("Starting Null Pointer Exception Demo.");
        
        // Step 1: Create an object that is null via an inter-procedural call.
        Object obj = createObject();

        try {
            // Step 2: Process the object which propagates the null value.
            processObject(obj);
        } catch (NullPointerException e) {
            System.out.println("Caught a NullPointerException: " + e.getMessage());
        }
    }

    // Function that simulates object creation but returns null.
    private static Object createObject() {
        System.out.println("createObject: Calling getNullObject...");
        return getNullObject();
    }

    // Helper function that explicitly returns null.
    private static Object getNullObject() {
        System.out.println("getNullObject: Returning null.");
        return null;
    }

    // Function that further propagates the object received.
    private static void processObject(Object obj) {
        System.out.println("processObject: Received object, calling useObject...");
        useObject(obj);
    }
    
    // Function that uses the object, causing a Null Pointer Exception if object is null.
    private static void useObject(Object obj) {
        System.out.println("useObject: Attempting to call toString on the object...");
        // This line will throw a NullPointerException if obj is null.
        System.out.println("Object's toString(): " + obj.toString());
    }
}