package good;
import java.util.ArrayList;

public class Test06 {
    static ArrayList<String> names;

    public static void test6_main(String[] args) {
        names = new ArrayList<String>();
        names.add("Dominic");
        System.out.println("Name length: " + names.size());
    }

    public static void main(String[] args) {
        test6_main(args);
    }
}