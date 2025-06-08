package bad;
public class Test04 {
    private static String test4_called(Boolean flag) {
        String str = flag ? "valid" : null;
        return str.toUpperCase();
    }

    private static void test4_caller() {
        System.out.println(test4_called(false));
    }

    public static void test4_main(String[] args) {
        test4_caller();
    }

    public static void main(String[] args) {
        test4_main(args);
    }
}