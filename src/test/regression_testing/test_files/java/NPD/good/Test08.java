public class Test08 {
    private static String test8_processString(String str) {
        return str.toUpperCase();
    }

    private static String test8_inner3(String str) {
        return test8_processString(str);
    }

    private static String test8_inner2(String str) {
        if (str == null) return test8_inner3("DefaUlt StriNg");
        return test8_inner3(str);
    }

    private static String test8_inner1(String str) {
        return test8_inner2(str);
    }

    public static void test8_main(String[] args) {
        System.out.print("Lowercase: ");
        String str = null;
        System.out.println(test8_inner1(str));
    }
}