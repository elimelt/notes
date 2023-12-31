package Misc;

/* https://leetcode.com/problems/reorder-data-in-log-files */

import java.util.ArrayList;
import java.util.List;

public class ReorderLog {
    public String[] reorderLogFiles(String[] logs) {
        List<String> let = new ArrayList<>();
        List<String> dig = new ArrayList<>();
        
        for (String s : logs) {
            if (Character.isLetter(s.charAt(s.indexOf(" ") + 1))) 
                let.add(s);
            else
                dig.add(s);
        }

        let.sort(
            (s1, s2) -> {
                String s1Sub = s1.substring(s1.indexOf(" "));
                String s2Sub = s2.substring(s2.indexOf(" "));

                return (s1Sub.equals(s2Sub)) 
                    ? s1.compareTo(s2)
                    : s1Sub.compareTo(s2Sub);
            }
        );

        let.addAll(dig);

        return let.toArray(new String[let.size()]);
    }
}
