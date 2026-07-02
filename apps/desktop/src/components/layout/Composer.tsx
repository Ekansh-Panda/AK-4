import { useRef, useState, type KeyboardEvent } from "react";
import { Paperclip, Mic, ArrowUp } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Textarea } from "@/components/ui/Input";
import { cn } from "@/lib/cn";

export interface ComposerProps {
  onSend: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
}

/**
 * Bottom composer: attach + mic + a growing textarea + send.
 * Enter sends, Shift+Enter newlines. The mic is a UI placeholder for now.
 */
export function Composer({ onSend, placeholder = "Talk to Miori…", disabled }: ComposerProps) {
  const [value, setValue] = useState("");
  const [listening, setListening] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const ref = useRef<HTMLTextAreaElement>(null);
  
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<BlobPart[]>([]);

  const submit = () => {
    const v = value.trim();
    if (!v || disabled) return;
    onSend(v);
    setValue("");
    if (ref.current) ref.current.style.height = "auto";
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  const autoGrow = () => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 180)}px`;
  };

  const toggleRecording = async () => {
    if (listening && mediaRecorderRef.current) {
      // Stop recording
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current.stream.getTracks().forEach((track) => track.stop());
      setListening(false);
      setIsProcessing(true);
    } else {
      // Start recording
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const mediaRecorder = new MediaRecorder(stream);
        mediaRecorderRef.current = mediaRecorder;
        audioChunksRef.current = [];

        mediaRecorder.ondataavailable = (e) => {
          if (e.data.size > 0) {
            audioChunksRef.current.push(e.data);
          }
        };

        mediaRecorder.onstop = async () => {
          const audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" });
          const formData = new FormData();
          formData.append("file", audioBlob, "audio.webm");

          try {
            // Hardcoded URL for now, but ideally uses api client
            const baseUrl = import.meta.env.VITE_MIORI_API || "http://localhost:8000/api";
            const res = await fetch(`${baseUrl}/audio/transcribe`, {
              method: "POST",
              body: formData,
            });
            if (res.ok) {
              const data = await res.json();
              if (data.text) {
                setValue((prev) => (prev ? prev + " " + data.text : data.text));
                setTimeout(autoGrow, 0);
              }
            } else {
              console.error("Transcription failed:", res.status, res.statusText);
            }
          } catch (e) {
            console.error("Transcription error:", e);
          } finally {
            setIsProcessing(false);
          }
        };

        mediaRecorder.start();
        setListening(true);
      } catch (err) {
        console.error("Failed to start recording", err);
      }
    }
  };

  return (
    <div className="glass rounded-lg p-2">
      <div className="flex items-end gap-2">
        <Button
          variant="ghost"
          size="icon"
          title="Attach file"
          aria-label="Attach file"
          disabled={disabled}
        >
          <Paperclip size={18} />
        </Button>

        <Textarea
          ref={ref}
          rows={1}
          value={value}
          placeholder={placeholder}
          disabled={disabled}
          onChange={(e) => {
            setValue(e.target.value);
            autoGrow();
          }}
          onKeyDown={onKeyDown}
          className="min-h-[2.5rem] border-0 bg-transparent focus:bg-transparent"
        />

        <Button
          variant="ghost"
          size="icon"
          title={listening ? "Stop listening" : "Voice input"}
          aria-label="Voice input"
          disabled={disabled || isProcessing}
          onClick={toggleRecording}
          className={cn(listening && "text-accent")}
        >
          <Mic size={18} className={cn(listening && "animate-orb-pulse", isProcessing && "animate-pulse opacity-50")} />
        </Button>

        <Button
          variant="primary"
          size="icon"
          title="Send"
          aria-label="Send message"
          disabled={disabled || !value.trim()}
          onClick={submit}
        >
          <ArrowUp size={18} />
        </Button>
      </div>
    </div>
  );
}
