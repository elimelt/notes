package Misc;

/* https://leetcode.com/problems/add-two-numbers */

import Misc.ListNode;

public class AddTwoNumbers {
    public ListNode addTwoNumbers(ListNode l1, ListNode l2) {
        if (l1 == null && l2 == null)
            return null;

        if (l1 == null) {
            if (l2.val >= 10) {
                l2.val -= 10;
                if (l2.next == null) {
                    l2.next = new ListNode(1);
                } else {
                    l2.next.val++;
                }
            }
            l2.next = addTwoNumbers(null, l2.next);
            return l2;
        }
    
        if (l2 == null) {
            return addTwoNumbers(null, l1);
        }

        int combined = l1.val + l2.val;

        if (l1.next == null && l2.next == null) {
            if (combined >= 10) {
                l1.next = new ListNode(1);
                l1.val = combined - 10;
            } else l1.val = combined;
            return l1;
        }

        
        if (combined >= 10) {
            if (l1.next == null) 
                l1.next = new ListNode(1);
            else 
                l1.next.val++;
            l1.val = combined - 10;
        } else l1.val = combined;

        l1.next = addTwoNumbers(l1.next, l2.next);
        return l1;
    }
}
