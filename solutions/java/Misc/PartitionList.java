package Misc;
import Misc.ReorderList.ListNode;

public class PartitionList {
    public ListNode partition(ListNode head, int x) {
        if (head == null || head.next == null)
            return head;
        

        ListNode curr = head, 
            lessHead = null, 
            geqHead = null,
            lessTail = null,
            geqTail = null;

        while (curr != null) {
            if (curr.val < x) {
                if (lessHead == null) {
                    lessHead = curr;
                    lessTail = curr;
                } else {
                    lessTail.next = curr;
                    lessTail = lessTail.next;
                }
            } else {
                if (geqHead == null) {
                    geqHead = curr;
                    geqTail = curr;
                } else {
                    geqTail.next = curr;
                    geqTail = geqTail.next;
                }
            }
            curr = curr.next;
        } 

        if (lessHead == null)
            return geqHead;

        lessTail.next = geqHead;
        
        if (geqHead != null)
            geqTail.next = null;

        return lessHead;
    }
}
