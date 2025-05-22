public class Test08 {
    private String test8_processString(String str) {
        return str.toUpperCase();
    }

    private String test8_inner3(String str) {
        return test7_processString(str);
    }

    private String test8_inner2(String str) {
        if (str == null) return test7_inner2("DefaUlt StriNg");
        return test7_inner3(str);
    }

    private String test8_inner1(String str) {
        return test7_inner2(str);
    }

    public static void test8_main(String[] args) {
        System.out.print("Lowercase: ");
        String str = null;
        System.out.println(test7_inner1(str));
    }
}