# Master Voice AI Agents with LiveKit: Full Course Transcript & Engineering Guide

**Video URL**: https://www.youtube.com/watch?v=n-hCOsVQQgA  
**Duration**: 01:09:19 (4,159 seconds)  
**Source**: LiveKit Official Workshop  

---

## 1. Introduction & Overview
> **Timestamp**: [00:00 - 03:03]
> **Summary**: Introduction to voice AI agents, pitfalls (interruptions, robotic cadence), LiveKit Agents architecture, SDK prerequisites.

**[00:02]** You've probably talked to a voice AI recently and maybe it was frustrating. Maybe it cut you off. Maybe it felt robotic. Here's the thing. Building a voice agent that actually feels natural is harder than it looks. But once you understand the fundamentals, you can build something that people genuinely want to talk to, don't mind talking to, and actually prefer to talk to. And

**[00:22]** that's what this workshop is about. You don't need prior experience with voice AI, machine learning, or real-time systems. I'll explain all of those concepts as we go. Voice AI hit an inflection point. Speechtoext models are faster and more accurate. LLMs can handle nuanced conversations. Text to speech sounds human. These pieces exist. The challenge is wiring them together

**[00:45]** into something that feels responsive and natural. Now, a year ago, building this required specialized engineering knowledge and months of hard work. Today, you can get a working voice agent running in just a few minutes. So, here's what you're going to learn throughout this workshop. First, how the voice pipeline works. That's VAD, ST, LLM, and TTS. And then, why latency

**[01:07]** matters and how to uh minimize it. You'll learn techniques for natural turntaking so your agent doesn't interrupt you mid-sentence. You'll add personality to your agent and set up provider failovers uh so that it stays online even when a service goes down. And later you'll integrate external tools and APIs. And by the end you'll build real workflows with handoffs and

**[01:30]** consent collection. And the result is that you'll have an agent that listens, thinks, and responds in real time, not a toy demo. A foundation that you can actually ship. Each lesson adds a new capability, and each one builds on the last. You'll use the LifeKit agents SDK for Python. LifeKit handles the real-time infrastructure so that you can focus on the uh agentic logic. But note

**[01:55]** that while this workshop uses Python, LifeKit also offers a TypeScript agents SDK if you prefer working in JavaScript or TypeScript. And these are the models that we'll use throughout the workshop. Uh but they're not the only options. The agents SDK supports a wide range of providers for each component. If you want to use Azure for ST, Enthropic for

**[02:17]** your LLM, and 11 Labs for your TTS, you can swap them out with just a few lines of code. The patterns that you're going to learn will apply regardless of which providers you choose. And we'll use LifeKit inference, which comes with credits, so you'll get access to all of these models so that you can follow along without spending any money. There's also uh written materials that

**[02:37]** go along with each video lesson, so you can use them as a reference while you code. And there's a link in the video description for that. Now, before you start the workshop, make sure that you have Python 311 or higher, the UV package manager, a code editor, a free Lifekit Cloud account, and the written guide open if you want to copy and paste code snippets. Again, there's links in

**[02:58]** the video description for all of these materials. So, got all that? Let's start

---

## 2. Voice Agent Foundations & Architecture
> **Timestamp**: [03:03 - 13:24]
> **Summary**: Mental model of voice pipeline (VAD, STT, LLM, TTS), latency budgets (sub-500ms target), network transports (WebRTC over UDP vs WebSockets/HTTP).

**[03:03]** building something. Before we write any code, let's build a mental model of how voice agents actually work. And by the end of this lesson, you'll understand which components make up a real-time voice agent, how they interact, and why latency is such a big deal. Throughout this workshop, you'll build a production quality voice assistant. It listens to

**[03:24]** callers in real time through LifeKit's Web RTC infrastructure. It streams speech to text, runs responses through an LLM, and converts them back to speech with texttospech. You'll add interruption handling using voice activity detection and semantic turn detection. And you'll wire up tool calls, conversation escalation, and metric collection. Every voice agent

**[03:47]** follows the same highle pipeline. There are four core components. Voice activity detection determines when the human is speaking. Without it, your agent wastes money uh processing silence and might interrupt the user mid-sentence. Speech to text transcribes audio into tokens the LLM can understand. You'll want to choose models that support your target

**[04:10]** languages and accents. The large language model generates the reply, prompts, planning, and tool integrations all live here. And text to speech converts the LLM response into audio that feels natural and on brand. Supporting components like background noise cancellation, noise suppression, and end of turn detectors help the agent behave like a good conversational

**[04:34]** partner. And you'll add several of these throughout the workshop. Now, the cascaded pipeline bad to ST to LLM to TTS shown here is currently the most popular approach. But there is an alternative and that is to use speechtoech or real-time models that can process audio directly without explicit transcription. Now that's not going to be covered here in this workshop, but

**[04:58]** look out for more videos on that subject coming very soon. Now humans expect conversational latency under 500 milliseconds. Every component in the pipeline adds delay. VAD is the fastest at 15 to 30 milliseconds. ST takes 200 to 600 milliseconds. Uh LLMs range from 100 milliseconds to a full second. TTS adds another 100 to 300 milliseconds. And so these all add up. And so you

**[05:26]** could be looking at anywhere from 400 milliseconds to 2 seconds total. Hey, how's it going? Good. How are you? I'm good. Just got back from lunch. What did you have? A burrito. Anything else you'd like to talk about? You know what? I I got to go. That felt painful, right? Each 2C delay adds up fast. In a real conversation, you'd probably give up after the second or

**[06:09]** third pause. Your users will do the same thing. Low latency agents keep pipelines streaming and parallel. They avoid blocking I/IO and they carefully choose providers that balance quality with speed. And you'll learn techniques for shaving off those milliseconds in later lessons. A real-time voice has uh different networking needs than text. Let's compare the options. HTTP over TCP

**[06:35]** is great for text request responses, but it has a problem for live audio. You see, TCP guarantees that packets arrive in order. If one packet gets lost, everything behind it has to wait until that packet is resent and received. That's called head of line blocking. For a web page, that's fine. For live speech, a 200 millisecond pause while waiting for a retransmit on a single

**[07:02]** packet ruins the entire experience. The other option is websockets. Web soockets are persistent and birectional, but they're still blocked by TCP retransmits under poor networking conditions. But then we have web RTC over UDP and which was designed for media. UDP doesn't guarantee packet order or delivery, which sounds bad until you realize that for live audio, skipping a lost packet

**[07:28]** is actually better than waiting for it. WebRTC builds smart handling on top of UDP. It uses Opus, a codec optimized for speech that compresses audio efficiency. Each packet carries a time stamp so the receiver knows exactly when to play it. A jitter buffer smooths out timing variations when packets arrive at uneven intervals. And an adaptive bit rate

**[07:52]** adjusts audio quality on the fly based on network conditions. All of this adds up to low latency even when the network isn't cooperating. So in practice, WebRTC lets your agent deliver first audio faster and stay responsive during packet loss and jitter. This workshop uses LiveKit's Web RTC infrastructure throughout. So let's set up a project. We're going to open up our terminal and

**[08:18]** initiate a new project using UV. So the d-bear flag, it creates a minimal project without any boilerplate uh files. Next, we're going to install some dependencies. So UV add lifkit agents uh solo and turn detector. And it's good to note here we're using LifeKit agents uh version 1.3. and then lifekit plugins noise cancellation and then python.vdv. So this installs the lifkit agents SDK

**[08:52]** with solar VAD and turn detection noise cancellation plugin and the python.v package for environment variables. Next, we need to go grab our uh API credentials from our LiveKit cloud dashboard. If you haven't created one yet, it's completely free. There's a link in the video description. So here on the dashboard, I'm going to go down to settings, API keys, and then I'm

**[09:14]** going to create a new key for this demo. And I'll just name this uh voice agent demo. And let's generate a new key. So these are the things that you're going to need. The websocket URL, the API key, and the API secret. And to make things easier, you can just copy and paste uh these environment variables right here. And of course, I'm going to delete my API key. So, this one is not

**[09:38]** going to work for you. Uh, but again, it's completely free. Just go ahead and set one up for yourself. So, let's go back to the editor and we'll create a newv file. And we'll go ahead and paste in those credentials. Again, we have our LifeKit URL, our LifeKit API key, and our LifeKit API secret. So, make sure that you save that file, and then you can close it. And also make sure that

**[09:59]** the file is in your project directory. Okay, let's go ahead and create another file um again in our project directory here. We're going to call it agent. py. And so this is going to be our starter agent. And I'm going to paste in some code here and we'll walk through it. Now again, if you're following along in the written guide, you can copy and paste

**[10:19]** the code as well from there. So at the top here, we've got our imports from the LifeKit agents SDK. The agent class defines your agents behavior. The agent server handles dispatching sessions. And the agent session configures the voice pipeline. We have a job context here which provides information about the current job when a particular uh participant joins. And then in our

**[10:42]** session start we have uh the room IO which provides options for configuring audio input and output. So in the agent session here you can see we're configuring our ST LLM and TTS and also our VAD. And just up here we have our basic instructions for this agent. you are a helpful voice AI agent. So very simple starter agent here for you. So let's go ahead and get this agent

**[11:05]** running and see what it does. So again, be sure that you have saved this file. Let's open up our terminal. So first thing that we need to do is download the required model files like the Solero VAD model. Now we only have to do this the very first time. So uvun uh agent.py and then download files. Now let's run the agent. So we can just do the same thing

**[11:26]** except remove the download files. So, u agent and then console. So, we're going to actually run this right here in the console. Hello. &gt;&gt; Hello. How can I assist you today? &gt;&gt; Oh, great. What What can you assist me with? &gt;&gt; I can help with a variety of tasks such as answering questions, providing information, assisting with writing and

**[11:49]** editing, helping with learning new topics, generating ideas, offering recommendations, and much more. What do you need? &gt;&gt; Very helpful. Thank you. Thank you very much. We'll we'll talk to you again later. Bye-bye. Very helpful assistant. Very nice. Now, to stop your agent from running, just press control C. Now, if you're having any issues here in the

**[12:06]** console, uh it could be your input or output device selection. Uh so, you can actually add some extra flags there to select your input device. List devices uh lists all of the devices that you have on your machine. And then you can use the device ID to set the input and output devices using the input device and output device flag. Now, voice agents deal with messy real world

**[12:29]** inputs. People mumble. They change their minds midsentence, and they ask things in ways that you never anticipated. So, starting to think about how you'll test these scenarios now will save you headaches later. Now, testing and metrics, they come up later uh in a later lesson, but start keeping a backlog of scenarios that you want to test as features land. Uh so think about

**[12:54]** like edge cases, different accents, background noises and interruptions. So now you have a working voice agent and you understand the core pipeline. The that VAD detects voice ST transcribes it. The LLM generates a response and TTS uh speaks it back. So, in the next lesson, you'll add semantic turn detection to prevent those awkward interruptions when an agent jumps in too

**[13:23]** early. Hey, I wanted to ask you um about

---

## 3. Natural Turn-Taking & Semantic Turn Detection
> **Timestamp**: [13:24 - 18:46]
> **Summary**: Limitations of decibel VAD, mid-sentence pauses, semantic turn detection via multilingual model to evaluate phrase completeness.

**[13:31]** &gt;&gt; Sure. What would you like? &gt;&gt; No, about the weather uh this weekend. Um because I'm um &gt;&gt; Oh, no. I'm planning a trip to um Sounds exciting. &gt;&gt; So that's what happens when your agent relies only on voice activity detection. It hears a pause and it thinks that you're done. But humans pause mid-sentence all the time. We think,

**[14:03]** we breathe, we change direction. Uh, a good conversational agent needs to understand when someone is actually finished speaking. And so turn detection decides when the agent should speak and when it should stay quiet. And without it, you would get interruptions. And the agent starts answering at every single pause, even if the human is still mid-sentence. And so in this lesson,

**[14:28]** you'll add a semantic turn detector that dramatically improves conversational quality. Now, voice activity detection spots human patterned audio, but humans pause, restart sentences, and trail off all the time. And so, VAD sees a pause and it thinks that you're done talking. But semantic detection looks at all of the the meaning of the sentence and it asks,

**[14:54]** does this feel like a complete thought? The most important job of a turn detector is to reduce unwanted interruptions. It also improves accuracy for the ST engine since it gets complete utterances instead of fragments and the latency impact is minimal only around 20 milliseconds. So the first thing that we'll need to do is add the turn detector extra to our environment. So in

**[15:19]** Python an extra is an optional uh set of dependencies that a package can include. So we're going to UV add lifkit agents turn detector. So, this pulls in a multilingual model uh that you'll reference in the code, right? So, we'll go ahead and import this multilingual model from our uh turn detector plugin. We'll go down to our agent session here and then we'll add into our agent

**[15:44]** session this uh turn detection and pass it the multilingual model. Now, save that. And that's all that you have to do. The session now emits turn events when the semantic model decides a speaker is finished. So, let's go ahead and test it out. All right, let's open up our terminal. We'll run uv run agent.py and console to run it in the console. Let's see if it's any better. Yeah. Hey,

**[16:09]** how's it going? &gt;&gt; Hey, I'm doing great. Thanks for asking. &gt;&gt; How about Can you tell me about um about a time when uh you you struggled to come up with something to say? &gt;&gt; Sure. Even though I'm designed to generate responses quickly, there are times when a question is very vague or complex and it can be challenging to provide me.

**[16:40]** &gt;&gt; Let's try to interrupt him and like just like tell me something else. Got it. Switching gears. Did you know that octopuses have three hearts in blue blood? Two of their hearts. &gt;&gt; Tell me um something about um dolphins. &gt;&gt; Absolutely. Dolphins are incredibly intelligent marine. &gt;&gt; Much better. Much better. Let's stop it. So, this single change dramatically

**[17:07]** improves conversational quality. The agent feels more patient and natural. And this prepares you for more advanced latency optimization in later lessons. So let's talk about some best practices. Now a few things that you can keep in mind when using turn detection is make sure that you combine it with VAD and noise control for best results. Different languages have different pause

**[17:33]** patterns as well and semantic models uh help to normalize this. It also coordinates with preemptive generation, which we're going to talk about in a future lesson. And this allows the LLM to start planning while it's still waiting for a clear end of turn. Here are a few scenarios worth testing. First, try rapidfire short sentences and compare that to a single long sentence

**[17:59]** with natural pauses. See how the agent handles each of these. Uh, second, add some background noise. turn on a TV or have someone talking nearby. Does the agent stay focused on your voice? And third, if you speak multiple languages, try switching languages midterm. The multilingual model should handle this gracefully. Add these to your testing backlog. The

**[18:22]** more scenarios you try, the more confident you'll be in how your agent behaves. So, with semantic turn detection in place, your agent no longer jumps in at every pause. It waits for complete thoughts before responding. In the next lesson, you'll give an agent a distinctive personality, uh, change its voice, and add fallback providers so that it survives outages. Now that

---

## 4. Personality, Voices & Multi-Provider Failover
> **Timestamp**: [18:46 - 26:11]
> **Summary**: Crafting concise system prompts (<3 sentences), custom voices (Cartesia Sonic-3), FallbackAdapters for STT, LLM, and TTS to guarantee 100% uptime.

**[18:47]** turntaking feels natural, it's time to make the agent sound on brand. In this lesson, you'll give the assistant a distinct personality, change its voice, and configure fallback adapters so that the agent survives provider outages. Voices aren't neutral speakers. How the LLM writes affects how the TTS sounds. So, first, match your phrasing to the voice. Shorter clauses and fewer

**[19:15]** parentheticals sound more natural when spoken. Second, be aware of dialect. Tailor spelling and idioms for authenticity, whether it's UK or US English. Third, use emotion control sparingly. Add subtle direction in system messages, but don't overdo it. And fourth, keep replies brief. Three sentences or fewer reduces latency and prevents your agent from monologuing.

**[19:42]** The system prompt and the voice work together as a team. They need to complement each other. Now, your system prompt sets expectations for tone and boundaries. So, let's update the assistant class with a more specific personality. So, back in our uh agent.py in the assistant, let's update the instructions. So, I'm defining who this agent is. It's an upbeat, slightly sarcastic voice AI

**[20:10]** or text support. It helps callers fix issues without rambling and keeps replies under three sentences. And you don't have to use this exact personality. Take some time to write instructions that make sense for your use case. Now, the key is being specific about tone, length, and boundaries. Next, let's modify the TTS configuration to match the new personality.

**[20:32]** So, if we go down here, we can see in our agent session all of our uh definitions here. And what we're looking for is TTS text to speech. So, currently we're using Cartisia Sonic 3. And we can add a specific voice ID to this. If we go over to the LiveKit docs and we can look at the specific Cartisia voices, we can actually play them here. So Blake is

**[20:55]** the default. &gt;&gt; Hi there. Nice to meet you. I'm looking forward to working with you. &gt;&gt; And there are others. &gt;&gt; Holaerte. &gt;&gt; Daniela is great for Spanish. Then there's Jacine. &gt;&gt; Hi there. Nice to meet you. I'm looking forward to working with you. &gt;&gt; Cool. So let's use Jacquine. So any of these voices, if you like them, uh, just

**[21:14]** copy the voice ID. Let's go back and update our voice ID now. So right here, Cartisia Sonic 3. Let's just go ahead and update that voice ID there. So now it's Cartisia Sonic 3 and then colon and then this is the actual voice ID here. And notice here that we have one model assigned to each component. But every provider has hiccups. When outages happen, you don't want your agent to

**[21:39]** stop working entirely. Production agents always need secondary providers. So lifekits fallback adapters automatically retry in priority order. So let's set up these fallback adapters. First let's go up to the top and we're going to import a few more things. We're going to import uh llm sttts and inference. And now let's go down. So instead of an individual component for each line,

**[22:03]** we're going to uh wrap each of these pipeline components with a fallback adapter. So for st it's going to look something like this. We have st equals st.fallback fallback adapter and then we are going to add in our uh again we're using the lifekit inference so inferencest from model string and then we're passing in assembly AI as our primary and our

**[22:26]** secondary will be deepgram nova 3 so I'll go ahead and do the same for the llm and the tts all right so now we have each of these set up with fallbacks we have openai as the primary and then gemini as the as a fallback for our LLM we have cartisia as the primary ary TTS and in world as our secondary. So these adapters degrade gracefully. If the first provider fails, the session

**[22:50]** retries the next one without dropping the call. Your users never know anything went wrong. Let's test this out. Be sure that you saved the file. Open up our terminal and we'll do uv run agents agent.py and then console. We should notice a different voice. Switching to my more charming, slightly sarcastic voice now. What tech trouble are we tackling today?

**[23:16]** &gt;&gt; Um, I'm having a problem connecting to my Wi-Fi. &gt;&gt; Uh, the classic Wi-Fi Houdini act. First, try turning your router off and on again because tech &gt;&gt; I did that already. Did that a million times. It's still not working. &gt;&gt; Persistent router taps. Got it. Next. Check if your devices Wi-Fi is actually turned on. and try. &gt;&gt; All right, your devices Wi-Fi is on. Good start. Try moving closer to the

**[23:48]** router to rule out &gt;&gt; something else. I'm actually um trying to log into my bank account. Can you help me with that? &gt;&gt; Sure thing. But for security reasons, I can't access your bank account. &gt;&gt; Ah, that's great. &gt;&gt; I can help if &gt;&gt; Okay, never mind. Stop. Okay, so seems to be working great. She's sarcastic. Um, we changed our voice. We've got our

**[24:10]** fallbacks. Let's test those fallbacks, actually. So, let's go up here and let's see. So, instead of GPT41, let's just do some uh in uh invalid model here. Uh, so we know that's not going to work. So, let's go ahead and test this out and see if it falls back to Gemini instead. So, we'll run a UV run agent. Hello. &gt;&gt; Hey there. Looks like you've stumbled

**[24:34]** into the land of helpful, slightly sarcastic tech support. What can I do for you? &gt;&gt; Um, yeah. Can you help me uh set up a brand new computer? &gt;&gt; Absolutely. Setting up a new computer is like unwrapping a present, &gt;&gt; but with more cables. To start, let's make sure you've got everything out of the box. &gt;&gt; Yeah. Yeah. Yeah. It's all out of the

**[24:58]** box, plugged in, ready to go. &gt;&gt; Fantastic. Is it powering on? And do you see anything on the screen? &gt;&gt; Yeah. So you can see here it is still working. Uh but we are of course getting errors which is good. We we love to see why it's not working. Uh but it is falling back to Gemini 2.5 because it obviously sees that OpenAI/invalid model is an invalid model. So of course

**[25:25]** uh we change this back to GPT41 mini. Save that. And let's go ahead and restart this. and it worked just fine with no errors. Hello. &gt;&gt; Hey there. What tech trouble can I zap away for you today? &gt;&gt; Oh, thank you. Sounds like you're working. So, this kind of chaos testing helps you confirm the agent will stay online even when a provider goes down.

**[25:52]** So, your agent now has a defined personality through the system prompt, a custom voice through the TTS configuration, and fallback adapters to handle provider outages. In the next lesson, you'll capture metrics so that you can measure performance and enable preemptive generation to reduce response latency. So, your agent now sounds great

---

## 5. Metrics, Preemptive Generation & LiveKit Cloud Deployment
> **Timestamp**: [26:11 - 44:59]
> **Summary**: TTFA (Time to First Audio), TTFT, EOU delay tracking, speculative execution / preemptive generation, LiveKit Cloud observability, trace spans, container deployment.

**[26:12]** and survives outages. But how do you know if it's actually performing well? This lesson covers three connected topics. Metrics collection to understand your agents behavior, deployment to LifeKit Cloud for production observability, and latency optimization techniques, including preemptive generation. So by the end you'll have real numbers to optimize against and the

**[26:35]** tools to track them in production. Now before we jump into the code, let's talk about what you're actually measuring. So time to first audio TTFA. This is the delay from when the user stops speaking to when they hear the first word of the response. This is the number users feel most directly. And then time to first token tracks when the LLM starts generating which helps isolate whether

**[27:00]** delays are coming from transcription the model or speech synthesis. You'll also track token usage for cost estimations, interruption rate to see how often users cut off the agent and fallback activations if your primary providers fail over. We're going to see these metrics show up in console logs during development and in LifeKit cloud's dashboard in production. The key

**[27:24]** takeaway here is going to be TTFA time to first audio. We want that to be less than 1 second for most responses. Let's start by collecting usage metrics. The first thing we're going to do is add some imports here. So, we're going to import agent state changed event metrics collected event metrics. Uh, all that comes from LifeKit agents. And then we're just going to define our logger

**[27:47]** here. And then we'll go down to our entry point function. So just before the session start, we've added this code block here. So let's break this down to see what this does. The usage collector aggregates data across all conversation turns. It tracks token counts for the LLM, audio durations for ST and TTS and cost estimates when available. The metrics collected event fires after each

**[28:12]** component finishes processing. You're capturing uh EOU metrics specifically, which stands for end of utterance. This is the moment when the the turn detector decides that the user has finished speaking and then when the uh worker shuts down log usage prints a summary so that you can see uh per session resource consumption. So the agent cycles through

**[28:35]** several states during a conversation listening thinking and speaking the agent state changed event. It fires each time the agent transitions between these states. When the agent enters the speaking state, you want to know how long the human waited. So, back in our code, below that code block that we just added, let's add another. And then be sure to uh import time up above here.

**[29:02]** We're using that in this new code block. So, this new block here, this gives you a real number to optimize against. You can watch the console output and see exactly how long users wait for each response. So, we'll see this being printed in the console after each response. Now, preemptive generation lets the LLM start forming a response before the user finishes speaking. The

**[29:25]** agent waits for a clear end of turn before actually speaking, but the thinking has already begun. We can enable this in a single line. If we go back up to our agent session, we're going to add another line here. And we're just going, it's just preemptive generation and equals true. That's it. And so this can save hundreds of milliseconds off of perceived latency,

**[29:49]** especially for longer uh user turns. The LLM gets a head start on generating the response. But that's not to say that preemptive generation is 100% good all of the time. Preemptive generation uh trades accuracy for speed. There are a few scenarios where uh this trade-off might not work in your favor. For instance, mids sentence direction changes. If a user says, "Book me a

**[30:13]** flight to New York." No, actually make that Chicago. The LLM might have already committed to New York. Second, complex multi-part instructions, long requests with multiple steps can get partially answered before the full context is available. Third, high accuracy domains, medical, legal, or financial applications where getting it right matters more than getting it fast. But

**[30:38]** for many conversational use cases, preemptive generation works well. But if you notice that the agent is uh jumping to conclusions or misinterpreting intent, consider disabling it or tuning your turn detection thresholds. So let's test out these metrics and see them in action. So go ahead and open up your terminal and we'll run uvun agent pi console.

**[31:08]** Hello agent, how are you? Hey there. I'm great. Thanks for asking. Ready to tackle your tech troubles? &gt;&gt; Yeah, let's see. What troubles am I having? Yeah, my my iPods have been like making crackling noises. What do you What's up with that? &gt;&gt; Crackling on iPods usually means dirty headphone jacks or a software glitch. &gt;&gt; Try clean.

**[31:28]** &gt;&gt; That sounds terrible. Okay, let's take a look at these metrics. So, let's go up to All right, so here we go. We've got some ST metrics here. We get the model name, the provider, and then the audio duration. Uh we've got some received user transcript here. Let's move on. ST metrics again. Received user transcript. Here's some ELOU metrics here. Again,

**[31:54]** multilingual provider. Uh end of utterance delay 65. Uh time to first audio. 8889 seconds. So, a lot of great information here that we can uh use to tune our agent. Now, when we press C to stop our agent, uh we then get this summary here, this nice little usage summary. This shows us the total tokens used, the total audio duration processed, and estimated costs if

**[32:23]** they're available. So we can see uh completion tokens there. Uh character counts, audio duration, ST audio duration versus TTS audio duration, LLM prompt tokens 154. So you now have visibility into your agents performance. The metrics show where time is spent, how many tokens are consumed, and how much audio is processed. So use this data to identify bottlenecks and

**[32:50]** optimize your pipeline. Remember this table from lesson one. With a best case total around 400 milliseconds, but a typical latency around 1 or two seconds, any TTFA under 1 second is solid. So, you're seeing about 800 milliseconds here, which puts this response in a good territory. Now, local testing and metrics is fine at first. Uh, but you'll want something much more robust in

**[33:16]** production. And so, you can use external tracing tools like Langfuse if you want. Uh, but LifeKit Cloud includes built-in observability for agent sessions. So, you can view transcripts, traces, logs, and even audio recordings directly in the LifeKit cloud dashboard without any uh additional steps. LiveKit's observability is also open telemetry compatible. So, you can also export

**[33:41]** traces to any open telemetry compatible backend if you prefer. Our dashboard here shows three synchronized views. The the transcripts with audio playback let you scrub through the conversation. You can hear exactly what happened. The traces tab breaks down each turn into spans for uh ST, LLM, TTS, and tool calls with detailed timestamps and durations. And then logs shows real-time

**[34:08]** messages from your agent server in chronological order. All of this data is synchronized to a single timeline which makes it so easy and so simple to see exactly what is happening under the hood. Now observability needs to be enabled in order to use it and we can do this at the project level. So go to your LiveKit dashboard and then under settings we'll go to

**[34:32]** project and then we can scroll down to data and privacy and then agent observability and just make sure that that is enabled and then go ahead and save your changes. Now once it's enabled all agent sessions will automatically record data. The agents SDK version uh for Python needs to be at least 1.3.0 or higher or 1.0.18. 0.18 or higher for NodeJS and recording happens

**[34:58]** automatically. You don't need to change your agent code at all. Audio is collected locally and then uploaded after the session ends along with transcripts and traces. Now, to view observability data in the dashboard, you will need to deploy your agent to LifeKit Cloud. Running locally is again fine for development, but we're at a place now where we want to start

**[35:19]** observing the performance of our agent. The decisions that we make from now on are going to have impacts on our agent and we want to know if a tool that we're adding or some feature that we're adding is introducing some poor performance. Now deploying to LifeKit Cloud gives you automatic scaling and load balancing. So your agent can handle multiple sessions

**[35:40]** without manual configuration. And the built-in observability integration means that transcripts, traces, and audio recordings upload automatically. Your agent runs on LifeKit's global network infrastructure, reducing latency for users worldwide, and you don't need to manage servers or containers yourself. So, it's a win-win. First, you'll need to make sure that you have the LifeKit

**[36:03]** CLI installed. If you don't have it uh installed yet, you can install it with Homebrew on Mac OS, or you can download the binary from the LifeKit documentation. There's a link in the video description. So once you have that installed, uh we'll do LifeKit Cloud O. So that's going to pop us over to LifeKit Cloud and ask us to confirm and we'll go ahead and select a project that

**[36:25]** we want to give it access to and we're going to hit allow access. Cool. Now we can go back to our uh code editor. So now deploying our agent is as simple as a single command. Okay. Agent create. You can specify which project if you have multiple, but I'll just go ahead and select this project. Yes, select the secrets. I already have my environment variables set up. Uh if you didn't

**[36:47]** already have them, then uh it would create them for you. So, we'll go ahead and select the existing environment variables. Uh we can select a region, US East or EU Central. So, I'll do US East. So, this command it it does several things. It registers your agent with LifeKit cloud and assigns a unique ID. The ID and the project configuration are written to a new LifeKit toml file. And

**[37:10]** if you don't already have a Docker file, the CLI is going to create that for you as well. And then it uploads your code to LifeKit Cloud's build service, builds a container image, and then deploys it to your project. So you can see the build logs here streaming to our terminal uh as the the CA container image is creating. And this usually just takes a minute or two depending on your

**[37:31]** dependencies. Now, once the deployment is complete, your agent is going to be live on LifeKit Cloud and ready to handle sessions. The agent automatically scales up and down based on demand. And all of the observability data will upload to the dashboard after each session. All right. So now it's asking me if I want to view logs. No, I don't care about logs. And we're done. So now

**[37:54]** let's test the deployed agent to generate some session data. So notice here we didn't have anything under agents. Let me refresh the page. And now we can see our new agent. It's here. So we can get an overview of our agents here. If we click on our agent, uh we can then see some more detailed information about our agent. But in order to test it, let's go over to

**[38:18]** sandbox and we're going to create a new sandbox. So we'll create a new web voice agent uh sandbox. And let's go ahead and create create this uh sandbox here. You can give it a name or just let it randomly generate a name. Let's go ahead and create it. And then we don't need these instructions. Let's go ahead and launch this. It's going to use our agent. So, let's go ahead and click

**[38:41]** start call and we'll need to enable the microphone. Hello. &gt;&gt; Hey there. What tech trouble can I zap for you today? &gt;&gt; Uh, more tech trouble. Um, I'm actually not having much tech trouble. Uh, so thank you. We'll go ahead and end the call. And now we should have some observability data on that really brief call there. Uh, but you can see it was

**[39:03]** still the same agent that we created. uh the same voice asking about tech trouble. Let's go ahead and go back over to our dashboard and this time let's go ahead and click on sessions and we can see our latest session here. We can click on it. We have this agent insights tab and this is where we can see our observability data and here is that timeline. So we can go ahead and click

**[39:26]** play here. Hello. &gt;&gt; Hey there. What tech trouble are we tackling today? &gt;&gt; Looks like I ended it before my last response um actually made its way up. So, um I probably should have talked a little bit longer, but you can see it recorded my audio, the agent's audio. So, the transcript view shows the conversation timeline with audio playback. You can scrub to any point and

**[39:54]** hear exactly what the user uh and agent said. In inline alerts, highlight key events like tool calls. And this view is great for spotting interruptions and understanding the conversation flow. So we can see here that the agent latency was 1.5 seconds. If we click on it, we can see some more stats. Now the trace view is where you'll spend most of your

**[40:16]** optimization time. Each agent response breaks down into spans for ST, LLM, and TTS. You can click on any of these and see extra details, timestamps, and durations. And this is where you can find and identify bottlenecks. If your LLM span is consistently over 500 milliseconds, you might consider a faster model or enabling preemptive generation if you haven't already. Uh if

**[40:42]** TTS is the bottleneck, try a different voice provider. So here again, we can click on the agent turn, we can see the LLM node and we can get all this extra information. Same with the TTS node and when the agent speaks, we get all of this uh extra details that can help us. So we can see exactly where time is spent in each turn. So in this example, we can see the LLM node is taking 793

**[41:06]** milliseconds. The TTS node is taking almost 2 seconds. So that's right there. That's where we can start considering optimization. So going over to the logs view, uh this is where it will show information, warnings, errors, and debug messages from your agent code, the media server, and client connections. So if something fails or you see unexpected behavior in the transcript, click here

**[41:31]** for the technical details. Again, we can click on each of these to show the extra information. Now, the really cool thing about observability here is that everything is all aligned to the same audio track. And so as we're scrubbing through the audio, we are in the same timeline looking at the same things in all of these uh all three of these different views. So they're all in sync.

**[41:54]** So if you have observability enabled at the project level, but you want to disable it for a specific session or for a specific agent, you can do that. So we'll just go down here to session start and then we can add an option here. We can add record equals false. Pretty simple. And now this agent will no longer collect observability data. So this disables the uh upload of audio

**[42:19]** transcripts, traces and logs for the entire session even if the project level setting is enabled. So use this when you need to handle sensitive data or you want to reduce storage costs for specific sessions. Now all observability data is stored in the US and is retained for 30 days and data older than 30 days is automatically deleted. Now you can download the audio transcripts and logs

**[42:42]** directly from the session if you need a copy. Now for projects on the free build plan, some uh anonymized session data may be retained longer for model improvement purposes. Uh paid plans including ship scale and enterprise have full data deletion after that 30-day window. A low latency voice requires parallel work across the stack. So here's some best practices. First,

**[43:06]** stream everything. ST LLM TTS should operate incrementally, not in big batches. Second, parallelize. Start uh TTS as soon as the LLM emits the first words. Don't wait for the full sentence. Third, avoid blocking IO. Keep tool calls and storage async. Bound your timeouts and retries. And fourth, keep prompts tight. Fewer tokens means faster first audio and lower cost. Now, the

**[43:34]** metrics you collect at the application level only tell you part of the story. Network conditions also affect perceived latency. WebRTC handles this with Opus audio compression, jitter buffering, and adaptive bit rate. If you see unexpectedly high time to first audio that doesn't correlate with your pipeline metrics, network conditions may be the culprit. Use agent observability

**[43:59]** to validate and and fine-tune agent performance. The trace view shows exactly where time is spent in each turn. So, this makes it easier to identify bottlenecks. So to recap, these are the metrics worth tracking as you continue building. You've seen them in the console output during development and in the trace view in production. And so aim for a time to first audio under 1

**[44:24]** second in most cases. And use the trace breakdown to identify which component to optimize when you're over budget. So you've learned which metrics matter for voice agents and how to collect them locally. You've improved latency with preemptive generation. You've deployed your agent to LifeKit Cloud, and you've seen how agent observability uh gives you transcripts, traces, and log views

**[44:49]** to debug and optimize each session. With metrics and observability in place, you can make datadriven decisions as you add tools and workflows in the next lesson.

---

## 6. Function Tools & MCP (Model Context Protocol)
> **Timestamp**: [44:59 - 56:36]
> **Summary**: Local @function_tool declarations, docstring prompting, console debugging, connecting external MCP servers, filler audio cues, and interruption safety.

**[45:00]** So, your agent can speak naturally, and you can measure its performance. Now, it's time to give it capabilities beyond conversation tools. Let your agent call external APIs, look up data, and take actions on behalf of users. And without tools, your agent can only respond based on what's in its training data and conversation context, and that's pretty

**[45:22]** limiting. Tools let you fetch real-time information like weather, stock prices, or order status. They let you take actions in external systems like creating tickets, sending emails, or updating records. You can access your private data from customer databases or internal docs. And you can trigger UI updates on the front end via RPC tools. Turn your agent from a chatbot into

**[45:49]** something that can actually get things done. So Lifegate uses the function tool decorator to expose Python functions to the LLM. The LLM decides when to call them based on the conversation context. So let's add a weather lookup tool. This example uses the open Matteo API which is free and doesn't require an API key. Okay, first thing at the top, let's

**[46:13]** import uh HTTP ex so that we can make HTTP requests and let's not forget to install that package as well. So, u add httpex. Then we also need to import some more things from lifekit agents. We need the function tool, the run context and the tool error. Let's go down to our instructions and let's update these as well. So, you are an upbeat, slightly sarcastic tech support, all that same

**[46:42]** stuff. Help the caller fix issues without rambling. Uh, but then we've added you can also look up the weather if asked. So, we're going to add this uh this function right here. And so, let's go ahead and walk through this. So, the the function tool decorator registers this method as a callable tool for the LLM. Then we have the context parameter which

**[47:06]** is a run context and this provides access to the current session, the speech handle for the interruption detection and any custom user data that you've stored. We've got our location. Now the dock string is critical here. The LLM reads the text to understand what the tool does and when it should be called. When a user says, "What is the weather in Paris?" The LLM scans through

**[47:32]** all of the available tools, reads each dock string, and decides which one matches the user's intent. A vague dock string means that the LLM might not call your tool when it should, or it might call it incorrectly. And the args section in the dock string is just as important. It tells the LLM what each parameter means and what values are appropriate. For location, here we are

**[47:56]** specify city name or location to get weather for. So the LLM knows to extract the city from the user's request. Without this description, the LLM might pass the wrong data or misunderstand what the parameter expects. So then here is our HTTP request where we are calling this uh geocod geocoding API from open mateo and we're going to pass in that location

**[48:23]** there and then we will basically just return those results. So if we go back down to the bottom here, we're returning the location, the temperature, and the condition. So then the LLM will have that information to then answer our question. Now notice we do have uh the tool error here. So if no location is found, it will return that. And so let's go ahead and test this. Let's see if it

**[48:46]** works. So make sure that you save this. Let's open up our terminal. And we'll do UV run agent. And then in the console. Now we could uh sync this with our our agent in the cloud which we deployed in the last lesson. Uh but for simple testing and development we can stay here in the console. Hey uh so what's what's the weather like in San Francisco? &gt;&gt; Currently it's 49.1 degrees Fahrenheit in San Francisco with clear conditions.

**[49:19]** &gt;&gt; Cool. What about in Tokyo? Tokyo is chilling at 42.6 degrees Fahrenheit right now with clear skies. &gt;&gt; Nice. &gt;&gt; Anything else I can about um What's the weather like on Mars? &gt;&gt; Mars? I wish I had that weather report for Earthly. I'm your go-to AI, but Martian weather might be. &gt;&gt; All right, it looks like it works. So,

**[49:45]** if we go down here, we can see that the uh the tool uh did get executed. So, look up weather. it passed the the location there with San Francisco and then it provided us the the the response there. Another really cool tool that we can use is MCP or model context protocol. This lets you connect to external tool servers. Now this is useful when you want to share tools

**[50:10]** across multiple agents. Tools are are managed maybe they're managed by separate teams or services or maybe you want to integrate with thirdparty uh MCP compatible systems. So let's connect to the LiveKit documentation MCP server. And so this turns our agent into a voice interface for searching LiveKit docs. So in our terminal, we'll uh UV add LiveKit

**[50:35]** agents MCP. And let's add another import here from LifeKit agents and that is MCP. And then we'll connect our MCP server to our session using MCP servers. that is going to be under agent session. So let's go find that agent session. We'll add another option here under agent session MCP servers and then we'll set the MCP server http to docs.livekit.io/mcp.

**[51:10]** And then lastly, let's go back up to our instructions and let's update these instructions to include everything. So, not only are we a a sarcastic um tech support person and we we try not to ramble, but we can also look up the weather and we can also answer questions about LifeKit by searching the documentation. When a user asks about LifeKit features, APIs, or how to build

**[51:33]** something, use the docs search tools to find accurate information. Amazing. So, when the session starts, it connects to the MCP server and fetches a list of the available tools. Each MCP tool then has a name and a description just like the the local function tool methods. So these MCP tools are automatically registered alongside your local tools and the LLM sees all of them together

**[51:58]** and it knows when to use them I guess somehow. I don't know. No, no, no. It uses the the tool descriptions from the MCP server uh to guide the LLM on when to use each tool. So let's go ahead and test this out. Again, make sure that you have saved this and then let's go ahead and UV run uh agents in the console again. Hello. &gt;&gt; Hey there. How can I help you with tech

**[52:22]** or live kit today? &gt;&gt; Yeah. So, um what uh what ST providers does live kit support? LiveKit supports these speechtoext SDT providers via LiveKit inference cloud service assembly AI English and six multilingual languages Cartisia Inc. Whisper 98 languages deepgram gram several English and multilingual models 11. &gt;&gt; How do I add a function tool to my

**[52:53]** agent? To add a function tool to your agent in LiveKit, you use the at@ function tool decorator on a method in your agent class. This lets the LLM access. &gt;&gt; We can see here in the terminal executing tool, the tool name is docs search and uh speech to text providers is what it passed in and so it used the tool and then uh here's tool execution

**[53:18]** completed. Uh it executed another tool get pages and so we can see it is using our MCP server perfectly. So now we could ask um anything. We could ask for tech support. We could ask for the weather. We could ask for something LifeKit related. So let's say um what is the weather like right now in Houston? &gt;&gt; The weather in Houston right now is around 70.4 degrees F and conditions are

**[53:45]** clear. Anything else you'd like to know? &gt;&gt; Yeah. Yeah. How can I quickly start up a new LiveKit agent? To quickly start a new LiveKit agent, your agent code first registers as an agent server process with the LiveKit server and waits for requests. When a user connects to a room, LiveKit dispatches a job request to an available agent server, which starts a new agent

**[54:09]** session process to handle the job. &gt;&gt; Regular explanation. Thank you so much for that. We'll talk to you later. Cool. So now the agent selects the right tool for each question. And the console logs, you can search through those and see which tool is being called and with which parameters. So let's take a look at a few best practices for tools. So be

**[54:27]** specific about what the tool does and when to use it. Uh keep tools fast under two seconds ideally or provide user feedback during long operations and then handle errors gracefully with the tool error exception and return meaningful data that helps the LLM form a good response. Now, some tools take a long time and and for those you'll want to give the user

**[54:54]** feedback and handle potential interruptions. So, to do that, um what we could do in any function tool, um we could add to that await context session say, let me search for that. So, we're adding that extra context. We're giving the user um confirmation that we're doing something. Now if your tool takes external actions that can't be rolled back uh then we can

**[55:21]** disable interruptions at the start. For instance, if um your tool creates an order uh is processing a payment, well that can't be undone. We don't want the user to interrupt that part of the agent session. And so for that we could go into any tool again uh just like we did here with this await context say we can do context.allow disallow interruptions.

**[55:46]** So that will prevent any interruptions once this tool is called. Uh there could be no interruptions until the tool returns. You can also add or remove tools at runtime based on conversation state. Here's what that could look like. We could add a tool dynamically. We could remove a tool. So, this is useful for progressive disclosure where you you're only showing certain tools after a user

**[56:10]** has been authenticated or reached a certain point in a workflow. Your agent can now call external APIs with function tools, connect to MCP servers for shared capabilities, and handle errors gracefully. And the LLMs automatically select the right tool based on what the user asks. In the final lesson, you're going to build production workflows for collecting consent and escalating to

**[56:35]** human agents. Your agent has tools. It

---

## 7. Production Workflows: Compliance Consent, Handoffs & Telephony
> **Timestamp**: [56:36 - 69:19]
> **Summary**: Structuring tasks with AgentTask, mandatory recording consent gates, escalation to supervisor agent with history transfer, SIP telephony integration.

**[56:38]** handles failures gracefully, and you can measure its performance. For production deployments, you'll also need to handle operational workflows like collecting consent and escalating to human agents when needed. Realworld voice agents need to do more than just answer questions. You need to collect recording consent before capturing calls, which is often

**[57:01]** legally required. You need to escalate to humans when the AI can't help or uh the user requests it. You need to handoff between specialized agents based on conversational context. And you need to preserve context across these transitions. So let's build these capabilities step by step. Tasks are focused units of work that complete and return a result. They're perfect for

**[57:27]** structured interactions like consent collection where you need a clear yes or no answer before proceeding. So let's build a task that collects recording consent. We're going to add another uh import here from live kit agents uh live agent task. So next we're going to define the consent task. So we have a new class here, collect consent, which extends the agent task. And so this is

**[57:52]** going to return a boolean true or false. The instructions ask for recording consent and get a clear yes or no answer. Be polite and professional. That's important. On enter, this method starts when the task starts. And so there's instructions here. Briefly introduce yourself and then ask for permission to record the call for quality assurance and training purposes.

**[58:13]** Make it clear that they can decline. And then we have two function tools. We have consent given and consent declined. And it basically just returns true or false. So now we can use this task in our main agent. So now if we go into our assistant first, let's go ahead and update our instructions. We're going to change these from our last agent. Uh you

**[58:34]** are a friendly customer service representative. Very simple. And then we don't need any of these other tools uh that we used in our last lesson. So we'll just go ahead and replace all of this. So here is our new uh assistant class. So you're a friendly customer service representative on enter collect consent. If we have consent then thank them and offer them your assistance. Uh

**[58:59]** if they declined consent let them know that you understand and you will proceed without recording. So this pattern keeps consent collection clean and separate from your main agent logic. So let's go ahead and try this out. Make sure you save it. Open up your terminal and let us run the agent in the console. &gt;&gt; Hello. Before we proceed, I'd like to

**[59:18]** introduce myself. I'm your assistant here to help with any questions or support you need. May I have your permission to record this call for quality assurance and training purposes? You are free to decline if you prefer. Could you please let me know if that is okay with you? A clear yes or no would be great. &gt;&gt; Yes. &gt;&gt; Thank you for your consent. How can I

**[59:39]** assist you today? &gt;&gt; Very good. So, it works. Now, if you're using LiveKit's agent observability features and you want session recordings to respect the user's consent choice, then you could start a new agent session with the record parameter set to false when uh consent is denied. This gives you fine grain control over which sessions get recorded. So, check the

**[60:02]** agent observability docs for uh more details on session level recording settings. Now, what happens when a user says they want to talk to a manager or escalate in some way? Let's take a look at that. Let's go ahead and add another class. So, this is going to be our manager agent. And here's the instructions. You are a customer service uh manager. You handle escalated

**[60:26]** escalated issues that frontline agents could not resolve. Be empathetic and solution focused. You have authority to offer refunds, credits, or other accommodations. Very nice. And we can also change uh the the voice here. Of course, we want to make sure that the voice is different because the manager obviously is a different person. So, let's go back into our main assistant

**[60:49]** agent and let's update the instructions. All right. So, you're a friendly customer service representative. Help customers with general inquiries. If they ask for a manager or you can't resolve their issue, use the escalate to manager tool. And so, let's go ahead and add that tool now. So escalate to manager uh is going to be transfer the customer to a manager when requested or

**[61:13]** you can't resolve their in their issue and return manager agent. So it's going to call that manager agent and say transferring you to a manager now. And so when a tool uh returns a new agent as the first value in the tupil, the session automatically hands off control to that agent. And the second value there is the message that is going to speak before that handoff completes.

**[61:38]** Now, by default, each agent starts fresh, but you usually want the manager to know what's already been discussed. So, we want to make sure that that conversation history persists. So, notice uh in the escalation tool here, uh in the manager agent, we're actually passing in that context here to the new agent. This carries the full conversation history to the manager. so

**[62:01]** they can pick up right where the previous agent left off. Let's give this one a whirl. &gt;&gt; Hello. Before we proceed, may I kindly ask for your permission to record this call for quality assurance and training purposes. Your consent is entirely voluntary and you may decline if you prefer. Could you please let me know if you agree to this recording?

**[62:26]** &gt;&gt; No. Thank you for letting me know. I understand and we'll proceed without recording. How can I assist you today? I really need to speak with a manager right now, please. &gt;&gt; I am transferring you to a manager now. They will assist you shortly. &gt;&gt; Hello, I'm the customer service manager. I understand you asked to speak with someone senior. I'm here to help. Could

**[62:54]** you please share the details of your concern so I can assist in resolving it? No concerns. I just wanted to speak to you. Thanks. Bye. How easy was that to get to a manager? Now, for complex workflows with multiple steps like collecting shipping information, uh you can use a task group. A task group lets you define multiple tasks that run in sequence. Each task has an ID and a

**[63:17]** description. And when the group completes, you can then access the results by that ID. And here is an example of a task group that collects both an email and shipping address. So first we're going to import our task group from agents beta workflows and then our agent task function tool and run context like we have in the past as well as this data class to define our uh

**[63:39]** email result and address result. And then we're just going to define two simple tasks. We have a get email task and a get address task. The get email task collects an email address and stores it in a data class. And then the um get address task does the same thing for the shipping address. And then in the checkout agent, uh we're going to create a task group. And then we're

**[64:02]** going to add both of those to the task group. Along with that, we will add an ID and a description for each. And each task is wrapped in a lambda so it can be uh reinitialized if the user needs to go back and make a correction. And then we just await that task group. And then it runs each task in sequence. And once complete, we access the results by their

**[64:23]** task ID and confirm the order details with the user. So one of the great things about task groups is they support going back to previous steps if the user needs to make corrections. So this makes multi-step data collection feel natural. And then for the ultimate escalation, uh you might need to transfer to an actual human agent. And so this typically

**[64:44]** involves SIP or telefan. So, first you'll want to disable interruptions so that the transfer message plays fully and then use the SIP integration to dial out to your phone system and bridge to a human agent. Now, SIP and telefan configuration is its own topic uh with more setup involved. And so, we'll have a separate videos that go deeper into telefan that's not going to be covered

**[65:08]** in this workshop. And so, don't worry if this part seems a little complex. For now, I'll show you the patterns for how human handoff works. And that would look like this. So we're going to import uh function tool run context uh and get a job context and then define this tool transfer to human and then transfer the call to a human agent. So we're going to

**[65:30]** disallow the interruption and then we're going to say I'm transferring you to a human agent now. Please hold on. So then we get the room context and then we await this uh publish SIP participant including the the SIP trunk ID and the dial to uh information that is specific to your SIP configuration. So then the SIP integration dials out to your phone

**[65:52]** system and bridges in the human agent. So a complete production uh agent flow might look like this. First, the consent task collects uh recording permission and then a triage agent determines the user's needs and then a specialized agent handles the specific request whether it's billing, support or sales and then escalations to a manager occurs uh as needed and then a human handoff is

**[66:22]** the last resort. Each transition preserves relevant context while allowing agents to have uh different personalities, tools, and permissions. Congratulations. You built a production quality voice agent from scratch. You covered ST, LLM, TTS, and why Web RTC matters for real-time audio. You you learned semantic turn detection to prevent awkward interruptions. You

**[66:49]** crafted system prompts, selected voices, and built fallback adapters for resilience. You measured performance and enabled preemptive generation. You connected your agent to external APIs and MCP servers. And you built production workflows with tasks and agent handoffs. Your agent can now listen in real time, respond naturally, call external services, collect

**[67:13]** structured information, and hand off to specialized agents, or even humans when needed. So, here is where you go next. Browse the Lifegate agents documentation for advanced topics like telefan, video processing, and real-time models. Explore the Python agents example repository for more complex workflows. Join the LifeKit community Slack to ask questions and share what you're

**[67:38]** building. And be sure to check out LifeKit Cloud for production hosting with built-in observability like we looked at. Links to all of these things are in the video description. And one more thing that I want to introduce you to is the LifeKit Cloud Agent Builder. Agent Builder is a visual tool that generates a basic voice agent in minutes. You configure the providers

**[68:00]** through the web interface. You set the system prompts and it generates the Python code for you that you can then download and even deploy directly from the interface. The code that agent builder generates is yours. You can download it, open it up in your own editor, customize it, add the tools, the workflows, and the custom logic that you learned in this workshop. Agent Builder

**[68:21]** gives you a great starting point. Everything that you learned here applies uh to extending that code. Now, why didn't we just start with Agent Builder? Well, it would have been much easier, yes, but uh I wanted you to see exactly how to start from scratch. Agent Builder can get you up and running quickly. Now, beyond the basics, you can also configure tools directly in the builder

**[68:44]** interface and test your agent with a built-in test interface before deploying. And when you're ready, oneclick deploy pushes your agent to LiveKit Cloud. If you want a full walkthrough of agent builder specifically, go check out our other video tutorial on that. I'll leave a link in the video description. You can find agent builder in your LifeKit cloud

**[69:04]** dashboard under agents. So go build a basic agent there, download the code, and you'll recognize those same patterns and components that you built from scratch here in this workshop. Now, I hope this workshop was helpful. Uh thank you for following along. Now go build something

---
