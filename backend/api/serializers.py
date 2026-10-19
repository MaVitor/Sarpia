from rest_framework import serializers
from django.conf import settings


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

    def validate_paginas(self, value):
        return _validar_paginas(value)


class AvaliacaoRequestSerializer(serializers.Serializer):
    paginas = PaginaTextoSerializer(many=True)
    ensaio = serializers.CharField(min_length=20, max_length=30000)
    modo = serializers.ChoiceField(choices=["pdf", "roteiro"], default="pdf")
    referencia = serializers.DictField(
        required=True,
        error_messages={
            "required": "Prepare os tópicos do material antes de avaliar o ensaio."
        },
    )

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


class PerguntasRequestSerializer(serializers.Serializer):
    paginas = PaginaTextoSerializer(many=True)
    quantidade = serializers.IntegerField(default=3, min_value=1, max_value=10)

    def validate_paginas(self, value):
        return _validar_paginas(value)
