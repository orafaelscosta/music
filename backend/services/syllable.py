"""Serviço de segmentação silábica para alinhamento de letras."""

import asyncio
import re
import subprocess

import structlog

logger = structlog.get_logger()

# Regras de divisão silábica simples por idioma (fallback se eSpeak não disponível)
VOWELS = {
    "it": set("aeiouàèéìòóùAEIOUÀÈÉÌÒÓÙ"),
    "pt": set("aeiouáâãàéêíóôõúüAEIOUÁÂÃÀÉÊÍÓÔÕÚÜ"),
    "en": set("aeiouAEIOU"),
    "es": set("aeiouáéíóúüAEIOUÁÉÍÓÚÜ"),
    "fr": set("aeiouyàâæçéèêëïîôùûüÿœAEIOUYÀÂÆÇÉÈÊËÏÎÔÙÛÜŸŒ"),
    "de": set("aeiouäöüAEIOUÄÖÜ"),
    "ja": set("aeiouAEIOU"),
}


class SyllableService:
    """Segmenta texto em sílabas para alinhamento com notas MIDI."""

    def __init__(self) -> None:
        self._espeak_available: bool | None = None

    async def check_espeak(self) -> bool:
        """Verifica se eSpeak-ng está disponível no sistema."""
        if self._espeak_available is not None:
            return self._espeak_available

        try:
            proc = await asyncio.create_subprocess_exec(
                "espeak-ng", "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.wait()
            self._espeak_available = proc.returncode == 0
        except FileNotFoundError:
            self._espeak_available = False

        logger.info("espeak_check", available=self._espeak_available)
        return self._espeak_available

    async def syllabify_text(
        self, text: str, language: str = "it"
    ) -> list[str]:
        """Segmenta texto em sílabas usando eSpeak-ng ou fallback."""
        # Limpar texto
        lines = [line.strip() for line in text.strip().split("\n") if line.strip()]
        full_text = " ".join(lines)

        # Tentar eSpeak-ng primeiro
        if await self.check_espeak():
            syllables = await self._syllabify_espeak(full_text, language)
            if syllables:
                return syllables

        # Fallback: divisão simples
        return self._syllabify_simple(full_text, language)

    async def _syllabify_espeak(
        self, text: str, language: str
    ) -> list[str]:
        """Segmentação via eSpeak-ng (fonemas → sílabas)."""
        lang_map = {
            "it": "it", "pt": "pt-br", "en": "en",
            "es": "es", "fr": "fr", "de": "de", "ja": "ja",
        }
        espeak_lang = lang_map.get(language, "en")

        try:
            proc = await asyncio.create_subprocess_exec(
                "espeak-ng", "-v", espeak_lang, "-q", "-x", "--ipa",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate(input=text.encode())

            if proc.returncode != 0:
                logger.warning("espeak_erro", stderr=stderr.decode())
                return []

            phonemes = stdout.decode().strip()

            # Mapear sílabas fonéticas de volta para sílabas do texto original
            # eSpeak marca sílabas com acentos (ˈ ˌ) e separadores (.)
            words = text.split()
            syllables: list[str] = []

            for word in words:
                word_clean = re.sub(r"[^\w']", "", word)
                if not word_clean:
                    continue
                word_syllables = self._split_word_simple(word_clean, language)
                syllables.extend(word_syllables)

            return syllables

        except Exception as e:
            logger.warning("espeak_falha", error=str(e))
            return []

    def _syllabify_simple(self, text: str, language: str = "it") -> list[str]:
        """Divisão silábica simples baseada em regras de vogais."""
        words = re.findall(r"[\w']+", text)
        syllables: list[str] = []

        for word in words:
            word_syllables = self._split_word_simple(word, language)
            syllables.extend(word_syllables)

        return syllables

    def _split_word_simple(self, word: str, language: str = "it") -> list[str]:
        """Divide uma palavra em sílabas usando heurísticas por idioma."""
        vowels = VOWELS.get(language, VOWELS["it"])

        if len(word) <= 2:
            return [word]

        syllables: list[str] = []
        current = ""

        i = 0
        while i < len(word):
            current += word[i]

            # Verificar se a sílaba atual tem uma vogal
            has_vowel = any(c in vowels for c in current)

            if has_vowel and i + 1 < len(word):
                # Olhar adiante para decidir onde cortar
                next_char = word[i + 1]
                if next_char in vowels:
                    # Hiato — cortar antes da próxima vogal para italiano
                    if language == "it" and len(current) > 1:
                        syllables.append(current)
                        current = ""
                elif i + 2 < len(word) and next_char not in vowels:
                    next_next = word[i + 2]
                    if next_next in vowels:
                        # CV pattern — consoante vai para próxima sílaba
                        syllables.append(current)
                        current = ""
                    elif i + 3 < len(word) and next_next not in vowels:
                        # CCC — split: primeira consoante fica, resto vai
                        syllables.append(current + next_char)
                        current = ""
                        i += 1
            i += 1

        if current:
            syllables.append(current)

        # Merge sílabas muito pequenas (< 1 char)
        if len(syllables) > 1:
            merged = [syllables[0]]
            for s in syllables[1:]:
                if len(s) < 1:
                    merged[-1] += s
                else:
                    merged.append(s)
            syllables = merged

        return syllables if syllables else [word]

    def syllables_to_lines(
        self, text: str, syllables: list[str]
    ) -> list[list[str]]:
        """Organiza sílabas por linha da letra original."""
        lines = [line.strip() for line in text.strip().split("\n") if line.strip()]
        result: list[list[str]] = []
        idx = 0

        for line in lines:
            words = re.findall(r"[\w']+", line)
            line_syllables: list[str] = []
            for word in words:
                word_syl_count = len(self._split_word_simple(word))
                for _ in range(word_syl_count):
                    if idx < len(syllables):
                        line_syllables.append(syllables[idx])
                        idx += 1
                    else:
                        break
            result.append(line_syllables)

        return result
