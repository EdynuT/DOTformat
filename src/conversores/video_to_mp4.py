import ffmpeg

def convert_video_to_mp4(video_file, output_file):
    try:
        stream = ffmpeg.input(video_file)
        stream = ffmpeg.output(stream, output_file, vcodec='libx264', acodec='aac')
        ffmpeg.run(stream, overwrite_output=True)
        return True, "Conversão concluída com sucesso."
    except Exception as e:
        return False, f"Erro na conversão: {str(e)}"