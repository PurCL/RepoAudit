public class TestCase3 {
    public static String test3_getData() {
        return null;
    }
    public static String test3_transformData(String data) {
        return data.toUpperCase();
    }
    public static String test3_main() {
        String data = test3_getData();
        return test3_transformData(data);
    }
    
    public static void main(String[] args) {
        try {
            test3_main();
        } catch (Exception e) {
            System.out.println("Case 3 Exception: " + e);
        }
    }
}