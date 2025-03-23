public class TestCase4 {
    public static String[] test4_getArray() {
        return new String[] { "Hello", null, "World" };
    }
    public static int test4_useArray() {
        String[] arr = test4_getArray();
        return arr[1].length();
    }
    
    public static void main(String[] args) {
        try {
            test4_useArray();
        } catch (Exception e) {
            System.out.println("Case 5 Exception: " + e);
        }
    }
}