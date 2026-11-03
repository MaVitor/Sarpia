from rest_framework import serializers
from django.conf import settings
from api.contexto import CONTEXTOS


def _validar_paginas(value):
    if not value:
        raise serializers.ValidationError("Envie pelo menos uma página.")
    if len(value) > settings.MAX_PAGINAS:
        raise serializers.ValidationError(
            f"Envie no máximo {settings.MAX_PAGINAS} páginas."
        )
    caracteres = sum(len(pagina["texto"].strip()) for pagina in value)
    if not caracteres:
        raise serializers.ValidationError("O material precisa conter texto útil.")
    if caracteres > settings.MAX_CARACTERES_MATERIAL:
        raise serializers.ValidationError(
            f"O material excede o limite de {settings.MAX_CARACTERES_MATERIAL} caracteres."
        )
    return value


class PaginaTextoSerializer(serializers.Serializer):
    numero = serializers.IntegerField(min_value=1)
    texto = serializers.CharField(allow_blank=True)


class TopicosRequestSerializer(serializers.Serializer):
    paginas = PaginaTextoSerializer(many=True)
    modo = serializers.ChoiceField(choices=["pdf", "roteiro"], default="pdf")
    titulo = serializers.CharField(max_length=255, required=False, default="Apresentação")
    contexto = serializers.ChoiceField(choices=CONTEXTOS, default="geral")

    def validate_paginas(self, value):
        return _validar_paginas(value)


class AvaliacaoRequestSerializer(serializers.Serializer):
    presentation_id = serializers.UUIDField(required=False)
    paginas = PaginaTextoSerializer(many=True, required=False)
    ensaio = serializers.CharField(min_length=20, max_length=30000)
    modo = serializers.ChoiceField(choices=["pdf", "roteiro"], required=False)
    referencia = serializers.DictField(required=False)
    idempotency_key = serializers.CharField(max_length=128, required=False)
    contexto = serializers.ChoiceField(choices=CONTEXTOS, required=False, default="geral")

    def validate_ensaio(self, value):
        if not value.strip():
            raise serializers.ValidationError("O ensaio precisa conter texto útil.")
        if len(value) > settings.MAX_CARACTERES_ENSAIO:
            raise serializers.ValidationError(
                f"O ensaio excede o limite de {settings.MAX_CARACTERES_ENSAIO} caracteres."
            )
        return value

    def validate_paginas(self, value):
        return _validar_paginas(value)

    def validate(self, attrs):
        if not attrs.get("presentation_id") and (
            not attrs.get("paginas") or not attrs.get("modo") or not attrs.get("referencia")
        ):
            raise serializers.ValidationError(
                "Informe a apresentação ou prepare os tópicos antes de avaliar."
            )
        return attrs


class PerguntasRequestSerializer(serializers.Serializer):
    paginas = PaginaTextoSerializer(many=True)
    quantidade = serializers.IntegerField(default=3, min_value=1, max_value=10)
    contexto = serializers.ChoiceField(choices=CONTEXTOS, default="geral")

    def validate_paginas(self, value):
        return _validar_paginas(value)
