import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: '密码学研究图谱 | Crypto Research Explorer',
  description: '可视化注册式加密（Registration-Based Encryption）领域的研究演化',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
