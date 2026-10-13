import type { Metadata } from "next";
import { ProfileEditor } from "@/components/preferences/profile-editor";
export const metadata: Metadata = { title: "Preference profile | PropTech Copilot" };
export default function PreferencesPage() { return <ProfileEditor />; }
