from rest_framework import serializers


class PaginaTextoSerializer(serializers.Serializer):
    numero = serializers.IntegerField(min_value=1)
    texto = serializers.CharField(allow_blank=True)


class TopicosRequestSerializer(serializers.Serializer):
    paginas = PaginaTextoSerializer(many=True)


class AvaliacaoRequestSerializer(serializers.Serializer):
    paginas = PaginaTextoSerializer(many=True)
    ensaio = serializers.CharField(min_length=20, max_length=30000)


class PerguntasRequestSerializer(serializers.Serializer):
    paginas = PaginaTextoSerializer(many=True)
    quantidade = serializers.IntegerField(default=3, min_value=1, max_value=10)
