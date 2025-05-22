public class Test03 {
    public static String[] test3_getArray() {
        return new String[] { "Hello", null, "World" };
    }
    public static int test3_useArray() {
        String[] arr = test3_getArray();
        return arr[1].length();
    }
    public static void test3_main(String[] args) {
        test4_useArray()
    }
}