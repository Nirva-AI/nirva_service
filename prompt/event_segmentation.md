# Event Segmentation

You will analyze a transcript of `user_name`'s day to provide insights and summaries. Your goal is to understand what happened and how the user felt throughout the day. Help them remember what's important to them and also guide them with personalized insight.

Today's Date: `{formatted_date}`

## Input Transcript

The following is a transcript from an audio recording of `user_name`'s day, including `user_name`'s speech and audible interactions, presented in chronological order.

**Critical Note on Speaker Attribution:** The provided transcript includes multiple speakers. It is crucial to **diligently distinguish between what `user_name` (e.g., Wei) said versus what others said.** Your analysis, particularly the `first_person_narrative` and `key_quote_or_moment`, must *only* reflect `user_name`'s direct speech, thoughts, and experiences. Do NOT attribute statements, sentiments, or experiences of other speakers to `user_name`. During your initial read-through in Step 1, make an internal note or mental flag whenever user_name is speaking versus when others are speaking. This will be crucial for accurate attribution in Step 2.

## Your Task

### Step 1: Transcript Segmentation and Context Identification

Carefully read the provided transcript. Divide it into distinct, meaningful events or episodes. An event represents a continuous period of time where the core context remains consistent.

Identify context shifts based on **MAJOR** changes only:

* Changes in location (moving from home to coffee shop, office to restaurant, etc.)
* Changes in people `user_name` is interacting with (switching from talking to Friend A to Friend B, or from group conversation to solo activity)
* Changes in core activity type (switching from work meeting to exercise, from social gathering to commute, etc.)
* Significant time gaps (clear breaks of 30+ minutes)

**Do NOT** create separate events for:

* Changes in conversation topics within the same interaction
* Brief interruptions or tangents during continuous activities
* Moving between closely related activities in the same location (e.g., eating then talking at the same restaurant)
* Natural flow of conversation between different subjects

**Examples of what constitutes a SINGLE event:**

* A 3-hour coffee shop conversation covering relationships, work, family, and future plans
* A dinner party with multiple people discussing various topics throughout the evening
* A phone call that covers several different subjects
* A work meeting that discusses multiple agenda items

**Examples of what constitutes SEPARATE events:**

* Coffee shop conversation (Event 1) → Driving home (Event 2) → Cooking dinner at home (Event 3)
* Solo morning routine (Event 1) → Work meeting with colleagues (Event 2) → Lunch with friend (Event 3)
* Group dinner (Event 1) → Walking to bar with same group (Event 2) → Late night solo reflection at home (Event 3)

When in doubt, err on the side of fewer, longer events rather than many short ones.

#### Identifying Primary Interactant(s) - Revised and Clarified Instructions

For each event, meticulously identify the Primary Interactant(s). These are the individual(s) `user_name` is directly speaking with or actively engaged in an activity with during that specific event segment.

**`user_name` is the Narrator, Not an Interactant with Herself:**

* You will be provided with `user_name`'s actual name (e.g., Wei). `user_name` is the central individual whose activities are being logged.
* **Crucially**, `user_name` (e.g., Wei) should **never** be listed as a Primary Interactant with herself. The goal is to identify other individuals she is interacting with.

**Prioritize Explicit Naming within the Event:**

* Look for direct introductions (e.g., "This is Trent," "My friend Ash").
* Listen for instances where `user_name` or another speaker addresses someone by name within the current event's dialogue.

**Contextual Clues for Upcoming Interactions:**

* If `user_name` states an intention to meet a specific person for an upcoming event (e.g., "I'm going to see Ash for our picnic," or "I'm meeting Trent for a movie"), use that name for the subsequent event if the context confirms they are indeed the person she meets.

**Strictly Avoid Name Carryover and Assumptions:**

* Do **NOT** carry over names of individuals from previous, distinct events unless they are clearly and continuously interacting with `user_name` into the new event.
* Do **NOT** use the name of someone `user_name` is merely talking about if that person is not actively participating in the current interaction.
* If a name was mentioned for an upcoming interaction but the actual interaction doesn't explicitly confirm that name, be cautious.

**Handling Unclear, Ambiguous, or Unnamed Interactants (Fallback Strategy):**

* If an interactant's specific name is not clearly and unambiguously identifiable from the direct dialogue or immediate context of that specific event segment:
  * Do **NOT** guess a name.
  * Do **NOT** borrow a name from a different context, a person merely mentioned, or `user_name` herself.
  * Instead, use a generic but contextually appropriate descriptor. Examples:
    * "Friend" (if context suggests a personal, informal one-on-one relationship)
    * "Companion" (for a sustained one-on-one interaction where the specific relationship isn't clear but "Friend" feels appropriate, and no name is evident)
    * "Colleague(s)" (if in a work setting)
    * "Group of friends/colleagues/people" (if multiple unnamed individuals are interacting with `user_name` simultaneously)
    * "Staff" (e.g., "Cafe Staff," "Restaurant Staff," "Store Clerk") for service interactions.
    * "Family Member" (if context indicates, e.g., "Mom," "Brother," without a specific name being used in that segment).

* The primary goal is accuracy based only on the information present for that event. It is better to use an accurate generic term (like "Friend" or "Companion") than an incorrect specific name.

**Distinguish Between Active Interactants and Subjects of Conversation:**

* Only list individuals as Primary Interactant(s) if they are actively speaking to or with `user_name`, or are directly involved in an activity with `user_name` during that event segment.
* People who are merely the topic of conversation but not present and participating should not be listed as interactants for that segment.
