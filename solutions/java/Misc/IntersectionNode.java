package Misc;

import java.util.HashSet;
import java.util.Set;
import Misc.ReorderList.ListNode;

public class IntersectionNode {
    public ListNode getIntersectionNode(ListNode headA, ListNode headB) {
        if (headA == null || headB == null)
            return null;

        Set<ListNode> set = new HashSet<>();

        ListNode curr = headA;

        while (curr != null) {
            set.add(curr);
            curr = curr.next;
        }

        curr = headB;

        while (curr != null && !set.contains(curr))
            curr = curr.next;

        return curr;
        
    }
}
