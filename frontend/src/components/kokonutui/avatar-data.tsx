import React, { ReactNode } from "react";
import { cn } from "@/lib/utils";

export interface AvatarPreset {
  id: number;
  svg: ReactNode;
  alt: string;
}

// RGB values for the per-avatar color ring on the stage
export const AVATAR_RGB: Record<number, string> = {
  1: "255, 0, 91",
  2: "255, 125, 16",
  3: "255, 0, 91",
  4: "137, 252, 179",
};

export const avatars: AvatarPreset[] = [
  {
    id: 1,
    svg: (
      <svg
        aria-label="Avatar 1"
        fill="none"
        height="40"
        role="img"
        viewBox="0 0 36 36"
        width="40"
        xmlns="http://www.w3.org/2000/svg"
      >
        <title>Avatar 1</title>
        <mask
          height="36"
          id=":r111:"
          maskUnits="userSpaceOnUse"
          width="36"
          x="0"
          y="0"
        >
          <rect fill="#FFFFFF" height="36" rx="72" width="36" />
        </mask>
        <g mask="url(#:r111:)">
          <rect fill="#ff005b" height="36" width="36" />
          <rect
            fill="#ffb238"
            height="36"
            rx="6"
            transform="translate(9 -5) rotate(219 18 18) scale(1)"
            width="36"
            x="0"
            y="0"
          />
          <g transform="translate(4.5 -4) rotate(9 18 18)">
            <path
              d="M15 19c2 1 4 1 6 0"
              fill="none"
              stroke="#000000"
              strokeLinecap="round"
            />
            <rect
              fill="#000000"
              height="2"
              rx="1"
              stroke="none"
              width="1.5"
              x="10"
              y="14"
            />
            <rect
              fill="#000000"
              height="2"
              rx="1"
              stroke="none"
              width="1.5"
              x="24"
              y="14"
            />
          </g>
        </g>
      </svg>
    ),
    alt: "Avatar 1",
  },
  {
    id: 2,
    svg: (
      <svg
        aria-label="Avatar 2"
        fill="none"
        height="40"
        role="img"
        viewBox="0 0 36 36"
        width="40"
        xmlns="http://www.w3.org/2000/svg"
      >
        <title>Avatar 2</title>
        <mask
          height="36"
          id=":R4mrttb:"
          maskUnits="userSpaceOnUse"
          width="36"
          x="0"
          y="0"
        >
          <rect fill="#FFFFFF" height="36" rx="72" width="36" />
        </mask>
        <g mask="url(#:R4mrttb:)">
          <rect fill="#ff7d10" height="36" width="36" />
          <rect
            fill="#0a0310"
            height="36"
            rx="6"
            transform="translate(5 -1) rotate(55 18 18) scale(1.1)"
            width="36"
            x="0"
            y="0"
          />
          <g transform="translate(7 -6) rotate(-5 18 18)">
            <path
              d="M15 20c2 1 4 1 6 0"
              fill="none"
              stroke="#FFFFFF"
              strokeLinecap="round"
            />
            <rect
              fill="#FFFFFF"
              height="2"
              rx="1"
              stroke="none"
              width="1.5"
              x="14"
              y="14"
            />
            <rect
              fill="#FFFFFF"
              height="2"
              rx="1"
              stroke="none"
              width="1.5"
              x="20"
              y="14"
            />
          </g>
        </g>
      </svg>
    ),
    alt: "Avatar 2",
  },
  {
    id: 3,
    svg: (
      <svg
        aria-label="Avatar 3"
        fill="none"
        height="40"
        role="img"
        viewBox="0 0 36 36"
        width="40"
        xmlns="http://www.w3.org/2000/svg"
      >
        <title>Avatar 3</title>
        <mask
          height="36"
          id=":r11c:"
          maskUnits="userSpaceOnUse"
          width="36"
          x="0"
          y="0"
        >
          <rect fill="#FFFFFF" height="36" rx="72" width="36" />
        </mask>
        <g mask="url(#:r11c:)">
          <rect fill="#0a0310" height="36" width="36" />
          <rect
            fill="#ff005b"
            height="36"
            rx="36"
            transform="translate(-3 7) rotate(227 18 18) scale(1.2)"
            width="36"
            x="0"
            y="0"
          />
          <g transform="translate(-3 3.5) rotate(7 18 18)">
            <path d="M13,21 a1,0.75 0 0,0 10,0" fill="#FFFFFF" />
            <rect
              fill="#FFFFFF"
              height="2"
              rx="1"
              stroke="none"
              width="1.5"
              x="12"
              y="14"
            />
            <rect
              fill="#FFFFFF"
              height="2"
              rx="1"
              stroke="none"
              width="1.5"
              x="22"
              y="14"
            />
          </g>
        </g>
      </svg>
    ),
    alt: "Avatar 3",
  },
  {
    id: 4,
    svg: (
      <svg
        aria-label="Avatar 4"
        fill="none"
        height="40"
        role="img"
        viewBox="0 0 36 36"
        width="40"
        xmlns="http://www.w3.org/2000/svg"
      >
        <title>Avatar 4</title>
        <mask
          height="36"
          id=":r1gg:"
          maskUnits="userSpaceOnUse"
          width="36"
          x="0"
          y="0"
        >
          <rect fill="#FFFFFF" height="36" rx="72" width="36" />
        </mask>
        <g mask="url(#:r1gg:)">
          <rect fill="#d8fcb3" height="36" width="36" />
          <rect
            fill="#89fcb3"
            height="36"
            rx="6"
            transform="translate(9 -5) rotate(219 18 18) scale(1)"
            width="36"
            x="0"
            y="0"
          />
          <g transform="translate(4.5 -4) rotate(9 18 18)">
            <path
              d="M15 19c2 1 4 1 6 0"
              fill="none"
              stroke="#000000"
              strokeLinecap="round"
            />
            <rect
              fill="#000000"
              height="2"
              rx="1"
              stroke="none"
              width="1.5"
              x="10"
              y="14"
            />
            <rect
              fill="#000000"
              height="2"
              rx="1"
              stroke="none"
              width="1.5"
              x="24"
              y="14"
            />
          </g>
        </g>
      </svg>
    ),
    alt: "Avatar 4",
  },
];

export function getAvatarById(id: number): AvatarPreset {
  return avatars.find((a) => a.id === id) || avatars[0];
}

export function parseAvatarId(avatarUrl?: string | null): number | null {
  if (!avatarUrl) return null;
  if (avatarUrl.startsWith("avatar:")) {
    const parsed = parseInt(avatarUrl.replace("avatar:", ""), 10);
    return isNaN(parsed) ? null : parsed;
  }
  const directNum = parseInt(avatarUrl, 10);
  if (!isNaN(directNum) && directNum >= 1 && directNum <= 4) {
    return directNum;
  }
  return null;
}

export function UserAvatar({
  avatarUrl,
  username,
  className,
  size = 36,
}: {
  avatarUrl?: string | null;
  username?: string | null;
  className?: string;
  size?: number;
}) {
  const avatarId = parseAvatarId(avatarUrl);

  if (avatarId !== null) {
    const avatar = getAvatarById(avatarId);
    return (
      <div
        className={cn(
          "relative overflow-hidden rounded-full flex items-center justify-center shrink-0 select-none bg-carbon-lift",
          className
        )}
        style={{ width: size, height: size }}
      >
        <div
          className="flex items-center justify-center"
          style={{
            transform: `scale(${size / 36})`,
            width: 36,
            height: 36,
          }}
        >
          {avatar.svg}
        </div>
      </div>
    );
  }

  if (avatarUrl && (avatarUrl.startsWith("http") || avatarUrl.startsWith("data:"))) {
    return (
      <div
        className={cn(
          "relative overflow-hidden rounded-full flex items-center justify-center shrink-0 select-none bg-carbon-lift",
          className
        )}
        style={{ width: size, height: size }}
      >
        <img
          src={avatarUrl}
          alt={username || "User avatar"}
          className="h-full w-full object-cover"
        />
      </div>
    );
  }

  // Fallback: Show avatar 1 or initials
  if (username) {
    return (
      <div
        className={cn(
          "relative overflow-hidden rounded-full flex items-center justify-center shrink-0 select-none bg-signal-orange/20 text-signal-orange font-bold font-mono",
          className
        )}
        style={{ width: size, height: size, fontSize: Math.max(10, size * 0.35) }}
      >
        {username.slice(0, 2).toUpperCase()}
      </div>
    );
  }

  // Default Avatar 1
  const defaultAvatar = avatars[0];
  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-full flex items-center justify-center shrink-0 select-none bg-carbon-lift",
        className
      )}
      style={{ width: size, height: size }}
    >
      <div
        className="flex items-center justify-center"
        style={{
          transform: `scale(${size / 36})`,
          width: 36,
          height: 36,
        }}
      >
        {defaultAvatar.svg}
      </div>
    </div>
  );
}
