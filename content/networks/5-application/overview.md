---
title: Application Layer Overview
category: Networks
tags: TCP, UDP, application layer, reliability, flow control, overhead
description: Covers the implementation of the application layer, the topmost layer of the TCP/IP network model. Discusses the role of protocols like TCP and UDP in providing reliability, flow control, and overhead management at the application level. Examines the key concepts and design considerations for application layer functionality.
---

# Application Layer Overview

Applications built upon TCP have the benefit of being able to transfer arbitrary length data. Also provides reliability and flow control. However, some applications may not require these features and may be better suited to use UDP. Some applications even need to use UDP because they can't handle the overhead of TCP (like skype or online gaming).